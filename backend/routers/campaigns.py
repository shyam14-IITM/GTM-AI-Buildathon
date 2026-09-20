from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from typing import List, Union
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func, update

from database import get_db, AsyncSessionLocal
from models import Campaign, CampaignStatus, User, Prospect, ProspectStage, AgentLog, KnowledgeDocument, PromptVersion
from schemas import CampaignCreate, CampaignUpdate, CampaignResponse, AgentLogResponse, FunnelMetricsResponse, KnowledgeUpload, WebhookReply, PromptVersionCreate, PromptVersionResponse
from auth import get_current_user
from graph.workflow import compiled_workflow
from sqlalchemy import func
import asyncio
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Initialize local HuggingFace embeddings
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
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

from fastapi import Query

@router.put("/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: uuid.UUID,
    payload: CampaignUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    try:
        if payload.name is not None:
            campaign.name = payload.name
        if payload.status is not None:
            campaign.status = payload.status
        if payload.config is not None:
            merged_config = dict(campaign.config)
            merged_config.update(payload.config)
            campaign.config = merged_config
            
        await db.commit()
        await db.refresh(campaign)
        return campaign
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Database update failed: {str(e)}")

@router.get("/{campaign_id}/logs")
async def get_campaign_logs(
    campaign_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Fetch chronological AgentLog entries for a campaign with pagination. 
    """
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    total_result = await db.execute(select(func.count(AgentLog.id)).where(AgentLog.campaign_id == campaign_id))
    total_count = total_result.scalar()
    
    result = await db.execute(
        select(AgentLog)
        .where(AgentLog.campaign_id == campaign_id)
        .order_by(AgentLog.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    logs = result.scalars().all()
    
    return {
        "total": total_count,
        "skip": skip,
        "limit": limit,
        "data": [
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
    }

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

@router.post("/{campaign_id}/knowledge", status_code=status.HTTP_201_CREATED)
async def seed_knowledge(
    campaign_id: uuid.UUID,
    payload: Union[KnowledgeUpload, List[KnowledgeUpload]],
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Chunk and embed knowledge into pgvector."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    uploads = payload if isinstance(payload, list) else [payload]
    
    total_chunks = 0
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    
    for upload in uploads:
        chunks = splitter.split_text(upload.content)
        if not chunks:
            continue
            
        vectors = embeddings.embed_documents(chunks)
        
        for chunk, vector in zip(chunks, vectors):
            doc = KnowledgeDocument(
                campaign_id=campaign_id,
                title=upload.title or upload.topic or "Knowledge Context",
                content=chunk,
                embedding=vector
            )
            db.add(doc)
            total_chunks += 1
            
    await db.commit()
    return {"message": f"Successfully embedded {total_chunks} knowledge chunks"}

@router.get("/{campaign_id}/knowledge")
async def get_knowledge(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Fetch all unique knowledge base documents uploaded to a campaign."""
    # Since docs are chunked, we can group by title or just return distinct titles.
    # We will return the first chunk's content of each distinct title to give a preview.
    result = await db.execute(
        select(KnowledgeDocument.title, KnowledgeDocument.content)
        .where(KnowledgeDocument.campaign_id == campaign_id)
        .order_by(KnowledgeDocument.created_at.asc())
    )
    docs = result.all()
    
    # Deduplicate by title to avoid showing every single chunk
    unique_docs = {}
    for title, content in docs:
        if title not in unique_docs:
            unique_docs[title] = content
            
    return [{"title": k, "preview": v[:150] + "..." if len(v) > 150 else v} for k, v in unique_docs.items()]

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

from services.discovery_service import discover_leads

@router.post("/{campaign_id}/discover")
async def discover_campaign_prospects(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Query Apollo.io for leads matching the campaign's ICP and insert them.
    """
    result = await db.execute(
        select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id)
    )
    campaign = result.scalars().first()
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    roles = campaign.targeting_criteria.get("roles", [])
    if not roles:
        raise HTTPException(status_code=400, detail="Campaign must have target roles configured to discover leads.")
        
    try:
        # Limit set to 20 for a solid demo batch
        found_leads = await discover_leads(roles, limit=20)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
    if not found_leads:
        return {"message": "Apollo returned 0 leads for these criteria.", "discovered_count": 0}

    # Fetch existing emails to prevent duplicates
    emails = [lead["email"] for lead in found_leads]
    existing_res = await db.execute(select(Prospect.email).where(Prospect.email.in_(emails)))
    existing_emails = set(existing_res.scalars().all())
    
    added = 0
    for lead in found_leads:
        if lead["email"] not in existing_emails:
            full_name = f"{lead['first_name'] or ''} {lead['last_name'] or ''}".strip()
            db.add(Prospect(
                campaign_id=campaign_id,
                email=lead["email"],
                linkedin_url=lead["linkedin_url"],
                stage=ProspectStage.DISCOVERED,
                enriched_data={
                    "name": full_name,
                    "company": lead["company_name"],
                    "title": lead["headline"]
                }
            ))
            added += 1
            
    if added > 0:
        await db.commit()
        
    return {"message": f"Successfully discovered and saved {added} leads via Apollo.", "discovered_count": added}

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
            
        # Fetch ALL prospects in DISCOVERED stage (IDs only to avoid DetachedInstanceError)
        result = await db.execute(
            select(Prospect.id).where(Prospect.campaign_id == campaign_id, Prospect.stage == ProspectStage.DISCOVERED)
        )
        prospect_ids = result.scalars().all()
        
        if not prospect_ids:
            print("No DISCOVERED prospects found for this campaign to execute.")
            return

        print(f"--- [Background Task] Found {len(prospect_ids)} prospects to process ---")
        
    for pid in prospect_ids:
        try:
            # Use a fresh session per prospect to prevent one dead connection from crashing the batch!
            async with AsyncSessionLocal() as prospect_db:
                # 1. Fetch fresh prospect
                prospect = await prospect_db.get(Prospect, pid)
                if not prospect:
                    continue
                
                # MID-EXECUTION PAUSE CHECK
                status_result = await prospect_db.execute(select(Campaign.status).where(Campaign.id == campaign_id))
                current_status = status_result.scalar()
                
                if current_status != CampaignStatus.LIVE:
                    print(f"--- [Background Task] Campaign status is {current_status}. Halting execution. ---")
                    break
                    
                print(f"\n--- [Background Task] Processing prospect {prospect.id} ---")
                
                initial_state = {
                    "campaign_id": str(campaign_id),
                    "prospect_id": str(prospect.id),
                    "icp_criteria": campaign.targeting_criteria,
                    "campaign_config": campaign.config,
                    "structured_prospect_data": {},
                    "current_status": prospect.stage.value,
                    "messages": []
                }
                
                try:
                    final_state = await compiled_workflow.ainvoke(initial_state)
                    print("Final Status:", final_state.get("current_status"))
                except Exception as e:
                    print(f"--- [Background Task] Error processing prospect {prospect.id}: {str(e)} ---")
                    # Update prospect stage so it doesn't get stuck in DISCOVERED limbo
                    prospect.stage = ProspectStage.REJECTED
                    prospect_db.add(AgentLog(
                        campaign_id=campaign_id,
                        prospect_id=prospect.id,
                        agent_name="System",
                        action="WORKFLOW_ERROR",
                        status="ERROR",
                        prompt_version="system",
                        details={"error": str(e)}
                    ))
                    await prospect_db.commit()
                    
        except Exception as outer_e:
            print(f"--- [Background Task] CRITICAL loop error on prospect {pid}: {str(outer_e)} ---")
            pass
            
        print("--- [Background Task] Sleeping for 8 seconds to respect rate limits... ---")
        await asyncio.sleep(8)
            
    print("\n--- [Background Task] Batch execution finished! ---")


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

@router.post("/webhook/reply", status_code=status.HTTP_200_OK)
async def process_inbound_reply(
    payload: WebhookReply,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook endpoint to simulate inbound email, SMS or LinkedIn replies.
    This triggers the Conversation Agent asynchronously to parse the reply and respond.
    """
    # Verify the prospect exists
    result = await db.execute(select(Prospect).where(Prospect.id == payload.prospect_id))
    prospect = result.scalars().first()
    
    if not prospect:
        raise HTTPException(status_code=404, detail="Prospect not found")
        
    campaign_id = prospect.campaign_id
    
    # Normally we'd run this asynchronously to not block the webhook provider,
    # but for the demo we'll run it synchronously or just queue it to run.
    from graph.nodes import conversation_node
    from graph.state import AgentState
    from langchain_core.messages import HumanMessage
    
    async def run_conversation_agent():
        print(f"--- [Webhook] Triggering Conversation Node for Prospect {prospect.id} ---")
        state = AgentState(
            prospect_id=prospect.id,
            campaign_id=campaign_id,
            icp_criteria={},
            structured_prospect_data={},
            current_status="Inbound_Reply",
            selected_channel=payload.channel,
            messages=[HumanMessage(content=payload.message_body)]
        )
        try:
            await conversation_node(state)
        except Exception as e:
            print(f"FAILED Conversation Node: {str(e)}")
            
    background_tasks.add_task(run_conversation_agent)
    
    return {"message": "Inbound reply queued for processing by Conversation Agent."}

@router.post("/{campaign_id}/prompts", response_model=PromptVersionResponse, status_code=status.HTTP_201_CREATED)
async def create_prompt_version(
    campaign_id: uuid.UUID,
    payload: PromptVersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Saves a new system prompt for a specific agent type and makes it active."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    # Deactivate all previous prompts for this agent_type
    await db.execute(
        update(PromptVersion)
        .where(PromptVersion.campaign_id == campaign_id, PromptVersion.agent_type == payload.agent_type)
        .values(is_active=False)
    )
    
    # Get highest version number
    result = await db.execute(
        select(func.max(PromptVersion.version_number))
        .where(PromptVersion.campaign_id == campaign_id, PromptVersion.agent_type == payload.agent_type)
    )
    max_version = result.scalar() or 0
    
    new_prompt = PromptVersion(
        campaign_id=campaign_id,
        agent_type=payload.agent_type,
        version_number=max_version + 1,
        prompt_text=payload.prompt_text,
        is_active=True
    )
    db.add(new_prompt)
    await db.commit()
    await db.refresh(new_prompt)
    
    return new_prompt

@router.get("/{campaign_id}/prompts", response_model=List[PromptVersionResponse])
async def list_active_prompts(
    campaign_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Lists the currently active prompts for all agent types in the campaign."""
    result = await db.execute(select(Campaign).where(Campaign.id == campaign_id, Campaign.user_id == current_user.id))
    if not result.scalars().first():
        raise HTTPException(status_code=404, detail="Campaign not found")
        
    result = await db.execute(
        select(PromptVersion)
        .where(PromptVersion.campaign_id == campaign_id, PromptVersion.is_active == True)
    )
    return result.scalars().all()

