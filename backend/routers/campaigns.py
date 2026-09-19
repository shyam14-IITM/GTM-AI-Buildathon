import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db, AsyncSessionLocal
from models import Campaign, User, Prospect, AgentLog
from schemas import CampaignCreate, CampaignUpdate, CampaignResponse
from auth import get_current_user
from graph.workflow import compiled_workflow

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

@router.get("/{campaign_id}/logs")
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
            "prospect_id": log.prospect_id,
            "agent_name": log.agent_name,
            "action": log.action,
            "status": log.status,
            "details": log.details,
            "created_at": log.created_at
        } for log in logs
    ]

async def run_campaign_agents_background(campaign_id: uuid.UUID, user_id: uuid.UUID):
    """
    Background worker that runs the LangGraph orchestration.
    It fetches a real prospect from the database to test the flow.
    """
    print(f"\\n--- [Background Task] Starting execution for Campaign {campaign_id} ---")
    
    async with AsyncSessionLocal() as db:
        # Fetch the campaign to get icp_criteria
        result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = result.scalars().first()
        if not campaign:
            print("Campaign not found.")
            return
            
        # Fetch ONE real prospect to test
        result = await db.execute(select(Prospect).where(Prospect.campaign_id == campaign_id))
        prospect = result.scalars().first()
        
        if not prospect:
            print("No prospects found for this campaign to execute.")
            return

        # Pass real data to the graph
        initial_state = {
            "campaign_id": str(campaign_id),
            "prospect_id": str(prospect.id),
            "icp_criteria": campaign.targeting_criteria,
            "structured_prospect_data": {},
            "current_status": prospect.stage.value,
            "messages": []
        }
        
    # Execute the graph asynchronously (ainvoke) because nodes are async
    final_state = await compiled_workflow.ainvoke(initial_state)
    
    print("--- [Background Task] Graph execution finished! ---")
    print("Final Status:", final_state.get("current_status"), "\\n")


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
        
    # Queue the background task
    background_tasks.add_task(run_campaign_agents_background, campaign_id, current_user.id)
    
    return {"message": "Execution started in the background", "campaign_id": campaign_id}

