import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db, AsyncSessionLocal
from models import Campaign, CampaignStatus, User, Prospect, ProspectStage, AgentLog
from schemas import CampaignCreate, CampaignUpdate, CampaignResponse, AgentLogResponse, FunnelMetricsResponse
from auth import get_current_user
from graph.workflow import compiled_workflow
from sqlalchemy import func
import asyncio

router = APIRouter(prefix="/campaigns", tags=["campaigns"])

@router.get("/", response_model=List[CampaignResponse])
async def get_campaigns(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all campaigns for the authenticated user."""
    result = await db.execute(select(Campaign).where(Campaign.user_id == current_user.id))
    campaigns = result.scalars().all()
    return campaigns

@router.post("/", response_model=CampaignResponse, status_code=status.HTTP_201_CREATED)
async def create_campaign(
    campaign_in: CampaignCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new campaign linked to the current user."""
    new_campaign = Campaign(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=campaign_in.name,
        config=campaign_in.config,
        targeting_criteria=campaign_in.targeting_criteria
    )
    db.add(new_campaign)
    await db.commit()
    await db.refresh(new_campaign)
    return new_campaign

@router.patch("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID,
    campaign_in: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Update a campaign. 
    JSONB fields (config, targeting_criteria) will be safely merged with existing data.
    """
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalars().first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Update simple fields
    if campaign_in.name is not None:
        campaign.name = campaign_in.name
    if campaign_in.status is not None:
        campaign.status = campaign_in.status
        
    # Safely merge JSONB fields
    if campaign_in.config is not None:
        # Create a new dict merging old config and new config
        merged_config = dict(campaign.config)
        merged_config.update(campaign_in.config)
        # SQLAlchemy needs to know the jsonb column changed, reassigning trigger an update
        campaign.config = merged_config
        
    if campaign_in.targeting_criteria is not None:
        merged_criteria = dict(campaign.targeting_criteria)
        merged_criteria.update(campaign_in.targeting_criteria)
        campaign.targeting_criteria = merged_criteria
        
    await db.commit()
    await db.refresh(campaign)
    return campaign

@router.get("/{campaign_id}/logs", response_model=List[AgentLogResponse])
async def get_campaign_logs(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch chronological AgentLog entries for a campaign. 
    Designed for easy binding in DronaHQ list/table components.
    """
    # Verify access
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    result = await db.execute(
        select(AgentLog).where(AgentLog.campaign_id == campaign_id).order_by(AgentLog.created_at.desc())
    )
    logs = result.scalars().all()
    
    return [
        {
            "id": log.id,
            "campaign_id": log.campaign_id,
            "prospect_id": log.prospect_id,
            "agent_name": log.agent_name,
            "action": log.action,
            "status": log.status,
            "prompt_version": log.prompt_version,
            "details": log.details,
            "created_at": log.created_at
        } for log in logs
    ]

@router.get("/{campaign_id}/metrics", response_model=FunnelMetricsResponse)
async def get_campaign_metrics(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch the aggregated funnel metrics (count of prospects by stage) for a campaign.
    """
    # Verify access
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Group by stage and count
    result = await db.execute(
        select(Prospect.stage, func.count(Prospect.id))
        .where(Prospect.campaign_id == campaign_id)
        .group_by(Prospect.stage)
    )
    counts = result.all()
    
    metrics = FunnelMetricsResponse()
    for stage, count in counts:
        # Convert Enum string to lowercase field name dynamically
        field_name = stage.value.lower()
        if hasattr(metrics, field_name):
            setattr(metrics, field_name, count)
            
    return metrics

@router.post("/{campaign_id}/seed")
async def seed_campaign_prospects(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Insert 5 mock prospects in DISCOVERED stage for testing the batch processor.
    """
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    mock_prospects = [
        {"email": "john.doe@example.com", "linkedin": "linkedin.com/in/johndoe1"},
        {"email": "sarah.connor@example.com", "linkedin": "linkedin.com/in/sarahc"},
        {"email": "alex.smith@example.com", "linkedin": "linkedin.com/in/alexsmith123"},
        {"email": "mia.wallace@example.com", "linkedin": "linkedin.com/in/miaw"},
        {"email": "tom.hanks@example.com", "linkedin": "linkedin.com/in/tomh"}
    ]
    
    mock_emails = [p["email"] for p in mock_prospects]
    result = await db.execute(select(Prospect.email).where(Prospect.email.in_(mock_emails)))
    existing_emails = set(result.scalars().all())
    
    added = 0
    for p in mock_prospects:
        if p["email"] not in existing_emails:
            db.add(Prospect(
                campaign_id=campaign_id,
                email=p["email"],
                linkedin_url=p["linkedin"],
                stage=ProspectStage.DISCOVERED
            ))
            added += 1
        
    if added > 0:
        await db.commit()
        
    return {"message": f"Successfully seeded {added} new prospects", "campaign_id": campaign_id}

async def run_campaign_agents_background(campaign_id: uuid.UUID, user_id: uuid.UUID):
    """
    Background worker that runs the LangGraph orchestration.
    It fetches all DISCOVERED prospects and processes them sequentially.
    """
    print(f"\\n--- [Background Task] Starting batch execution for Campaign {campaign_id} ---")
    
    async with AsyncSessionLocal() as db:
        # Fetch the campaign to get icp_criteria
        result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = result.scalars().first()
        if not campaign:
            print("Campaign not found.")
            return
            
        # Fetch ALL prospects in DISCOVERED stage
        result = await db.execute(
            select(Prospect).where(Prospect.campaign_id == campaign_id, Prospect.stage == ProspectStage.DISCOVERED)
        )
        prospects = result.scalars().all()
        
        if not prospects:
            print("No DISCOVERED prospects found for this campaign to execute.")
            return

        print(f"--- [Background Task] Found {len(prospects)} prospects to process ---")
        
        for prospect in prospects:
            # MID-EXECUTION PAUSE CHECK
            # We re-fetch the campaign status just in case it was paused during a previous loop
            status_result = await db.execute(select(Campaign.status).where(Campaign.id == campaign_id))
            current_status = status_result.scalar()
            
            if current_status != CampaignStatus.LIVE:
                print(f"--- [Background Task] Campaign status is {current_status}. Halting execution. ---")
                break
                
            print(f"\\n--- [Background Task] Processing prospect {prospect.id} ---")
            
            # Pass real data to the graph
            initial_state = {
                "campaign_id": str(campaign_id),
                "prospect_id": str(prospect.id),
                "icp_criteria": campaign.targeting_criteria,
                "structured_prospect_data": {},
                "current_status": prospect.stage.value,
                "messages": []
            }
            
            try:
                # Execute the graph asynchronously (ainvoke)
                final_state = await compiled_workflow.ainvoke(initial_state)
                print("Final Status:", final_state.get("current_status"))
            except Exception as e:
                print(f"--- [Background Task] Error processing prospect {prospect.id}: {str(e)} ---")
                # Log the error so the UI can show it, and continue to the next prospect!
                db.add(AgentLog(
                    campaign_id=campaign_id,
                    prospect_id=prospect.id,
                    agent_name="System",
                    action="WORKFLOW_ERROR",
                    status="ERROR",
                    prompt_version="system",
                    details={"error": str(e)}
                ))
                await db.commit()
            
            # Rate Limit Protection: Sleep to avoid hitting Gemini Free Tier 20 RPM limits
            # 8 seconds * 2 LLM calls per prospect = well under 20 requests per minute!
            print("--- [Background Task] Sleeping for 8 seconds to respect rate limits... ---")
            await asyncio.sleep(8)
            
    print("\\n--- [Background Task] Batch execution finished! ---")


@router.post("/{campaign_id}/execute", status_code=status.HTTP_202_ACCEPTED)
async def execute_campaign(
    campaign_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Triggers the AI orchestration for a campaign. 
    Returns 202 Accepted instantly while the agents run in the background.
    """
    # Verify access
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalars().first()
    
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    if campaign.status != CampaignStatus.LIVE:
        raise HTTPException(status_code=400, detail=f"Cannot execute campaign with status: {campaign.status.value}")
        
    # Queue the background task
    background_tasks.add_task(run_campaign_agents_background, campaign_id, current_user.id)
    
    # We optionally can count discovered prospects just for the initial response payload
    result = await db.execute(
        select(func.count(Prospect.id)).where(Prospect.campaign_id == campaign_id, Prospect.stage == ProspectStage.DISCOVERED)
    )
    queued_count = result.scalar()
    
    return {"message": "Execution started in the background", "campaign_id": campaign_id, "queued": queued_count}

