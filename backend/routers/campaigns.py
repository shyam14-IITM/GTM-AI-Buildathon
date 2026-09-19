import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models import Campaign, User
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

async def run_campaign_agents_background(campaign_id: uuid.UUID, user_id: uuid.UUID):
    """
    Background worker that runs the LangGraph orchestration.
    In a real app, this would query the prospects for the campaign and iterate over them.
    For now, we just invoke the graph once with a dummy prospect to test the edges.
    """
    print(f"\\n--- [Background Task] Starting execution for Campaign {campaign_id} ---")
    
    # We pass the initial state to the graph
    initial_state = {
        "prospect_id": "test-prospect-123",
        "icp_criteria": {"industry": "Software", "min_revenue": "1M"},
        "structured_prospect_data": {},
        "current_status": "Discovered",
        "messages": []
    }
    
    # Execute the graph
    final_state = compiled_workflow.invoke(initial_state)
    
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

