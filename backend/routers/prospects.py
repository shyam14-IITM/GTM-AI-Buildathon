import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from database import get_db
from models import Prospect, Campaign, User, ProspectStage, AgentLog
from schemas import ProspectResponse, FunnelMetricsResponse, ProspectUpdate
from auth import get_current_user
from fastapi import Query

router = APIRouter(prefix="/prospects", tags=["prospects"])

async def verify_campaign_access(campaign_id: uuid.UUID, current_user: User, db: AsyncSession):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=403, detail="Not authorized to access this campaign")

@router.get("/{campaign_id}")
async def get_prospects(
    campaign_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all prospects for a specific campaign with pagination."""
    await verify_campaign_access(campaign_id, current_user, db)
    
    total_result = await db.execute(select(func.count(Prospect.id)).where(Prospect.campaign_id == campaign_id))
    total_count = total_result.scalar()
    
    result = await db.execute(
        select(Prospect)
        .where(Prospect.campaign_id == campaign_id)
        .offset(skip)
        .limit(limit)
    )
    prospects = result.scalars().all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "data": prospects
    }

@router.put("/{prospect_id}", response_model=ProspectResponse)
async def update_prospect(
    prospect_id: uuid.UUID,
    payload: ProspectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Allow a human rep to override a prospect's state via DronaHQ"""
    result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
    prospect = result.scalars().first()
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
        
    # Verify campaign access
    await verify_campaign_access(prospect.campaign_id, current_user, db)
    
    # Store old stage for logging if it changed
    old_stage = prospect.stage.value
    
    if payload.current_status is not None:
        try:
            prospect.stage = ProspectStage(payload.current_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid stage: {payload.current_status}")
            
    try:
        if payload.notes is not None:
            prospect.notes = payload.notes
            
        if payload.assigned_rep_id is not None:
            prospect.assigned_rep_id = payload.assigned_rep_id
        
        # Create audit log
        db.add(AgentLog(
            campaign_id=prospect.campaign_id,
            prospect_id=prospect.id,
            agent_name=current_user.name,
            action="MANUAL_OVERRIDE",
            status="SUCCESS",
            prompt_version="manual",
            details={
                "old_stage": old_stage, 
                "new_stage": prospect.stage.value,
                "notes": payload.notes,
                "assigned_rep_id": payload.assigned_rep_id
            }
        ))
        
        await db.commit()
        await db.refresh(prospect)
        return prospect
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")

@router.get("/{campaign_id}/funnel", response_model=FunnelMetricsResponse)
async def get_funnel_metrics(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get aggregated counts of prospects by stage for a campaign."""
    await verify_campaign_access(campaign_id, current_user, db)
    
    # GROUP BY query to count prospects by stage
    result = await db.execute(
        select(Prospect.stage, func.count(Prospect.id))
        .where(Prospect.campaign_id == campaign_id)
        .group_by(Prospect.stage)
    )
    
    metrics = {
        "discovered": 0,
        "researched": 0,
        "qualified": 0,
        "contacted": 0,
        "engaged": 0,
        "meeting": 0,
        "opportunity": 0,
        "rejected": 0
    }
    
    for stage, count in result.all():
        stage_val = stage.value.lower()
        if stage_val in metrics:
            metrics[stage_val] = count
            
    return FunnelMetricsResponse(**metrics)
