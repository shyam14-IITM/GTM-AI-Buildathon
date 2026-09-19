import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from database import get_db
from models import Prospect, Campaign, User, ProspectStage
from schemas import ProspectResponse, FunnelMetricsResponse
from auth import get_current_user

router = APIRouter(prefix="/prospects", tags=["prospects"])

async def verify_campaign_access(campaign_id: uuid.UUID, current_user: User, db: AsyncSession):
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=403, detail="Not authorized to access this campaign")

@router.get("/{campaign_id}", response_model=List[ProspectResponse])
async def get_prospects(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all prospects for a specific campaign."""
    await verify_campaign_access(campaign_id, current_user, db)
    
    result = await db.execute(select(Prospect).where(Prospect.campaign_id == campaign_id))
    return result.scalars().all()

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
