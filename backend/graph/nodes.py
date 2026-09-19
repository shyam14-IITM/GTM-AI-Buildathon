from typing import Any, Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_huggingface import HuggingFaceEmbeddings
from sqlalchemy.future import select

from .state import AgentState
from database import AsyncSessionLocal
from models import Prospect, ProspectStage, AgentLog, KnowledgeDocument, Campaign

# Initialize global embeddings for nodes
embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

class ICPDecision(BaseModel):
    status: Literal['Qualified', 'Rejected']
    reasoning: str

async def research_node(state: AgentState) -> dict[str, Any]:
    """
    The Research Node.
    Responsible for taking raw prospect identifiers (e.g., email/linkedin),
    executing search tools (Tavily/Exa), and structuring the data.
    """
    prospect_id = state.get('prospect_id')
    campaign_id = state.get('campaign_id')
    print(f"--- [Node: Research] Extracting data for Prospect ID: {prospect_id} ---")
    
    # 1. Update the Database using SQLAlchemy to get the real email
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        
        if prospect:
            # Parse the name from the email (e.g., john.doe@example.com -> John Doe)
            email = prospect.email or ""
            name_part = email.split('@')[0]
            prospect_name = name_part.replace('.', ' ').title() if name_part else "Jane Doe"
            
            # Format a realistic synthetic JSON profile
            mock_structured_data = {
                "name": prospect_name,
                "title": "CTO",
                "company_size": "200-500",
                "industry": "B2B SaaS",
                "geography": "United States",
                "recent_news": "Recently raised Series B funding"
            }
            
            prospect.stage = ProspectStage.RESEARCHED
            prospect.enriched_data = mock_structured_data
            
            # 3. Write to AgentLog
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="Research Node",
                action="ENRICHED",
                status="SUCCESS",
                prompt_version="v1.0",
                details={"structured_data": mock_structured_data}
            ))
            
            await db.commit()
            
    return {"structured_prospect_data": mock_structured_data}

async def icp_fitment_node(state: AgentState) -> dict[str, Any]:
    """
    The ICP Fitment Node.
    Evaluates the `structured_prospect_data` against the `icp_criteria` to determine 
    if the prospect is 'Qualified' or 'Rejected' using Gemini structured output.
    """
    print("--- [Node: ICP Fitment] Evaluating prospect fit via LLM ---")
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    icp_criteria = state.get("icp_criteria", {})
    structured_data = state.get("structured_prospect_data", {})
    
    system_prompt = SystemMessage(content="""
    You are a strict SDR evaluator. Your job is to compare prospect data against ICP criteria.
    Output a structured decision containing 'status' (Qualified or Rejected) and a brief 'reasoning'.
    """)
    
    user_prompt = HumanMessage(content=f"""
    ICP Criteria: {icp_criteria}
    Prospect Data: {structured_data}
    """)
    
    import os
    
    # Instantiate Groq (OpenAI compatible) and bind structured output
    llm = ChatOpenAI(
        model="openai/gpt-oss-20b",
        api_key=os.getenv("GROQ_API_KEY", "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"),
        base_url="https://api.groq.com/openai/v1",
        temperature=0
    )
    structured_llm = llm.with_structured_output(ICPDecision, include_raw=True)
    
    # Invoke asynchronously
    response = await structured_llm.ainvoke([system_prompt, user_prompt])
    decision: ICPDecision = response["parsed"]
    raw_msg = response["raw"]
    
    usage = raw_msg.usage_metadata or {}
    print(f"LLM Decision: {decision.status} - {decision.reasoning}")
    
    # Prepare details payload with meta
    details = {"status": decision.status, "reasoning": decision.reasoning}
    if usage:
        details["meta"] = {
            "model": "openai/gpt-oss-20b (Groq)",
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    
    # Update the Database using SQLAlchemy
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            prospect.stage = ProspectStage.QUALIFIED if decision.status == "Qualified" else ProspectStage.REJECTED
            
            # Write to AgentLog
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="ICP Fitment Node",
                action="EVALUATED_FIT",
                status="SUCCESS",
                prompt_version="v1.0",
                details=details
            ))
            
            await db.commit()
            
    return {
        "current_status": decision.status,
        "messages": [SystemMessage(content=f"ICP Fitment Reasoning: {decision.reasoning}")]
    }

class StrategyDecision(BaseModel):
    channel: Literal['email', 'linkedin']
    reasoning: str

async def strategy_node(state: AgentState) -> dict[str, Any]:
    """
    The Outreach Strategy Node.
    Decides which channel (Email or LinkedIn) to prioritize based on the campaign's configuration
    and the prospect's profile.
    """
    print("--- [Node: Strategy] Deciding outreach channel ---")
    campaign_id = state.get("campaign_id")
    prospect_id = state.get("prospect_id")
    structured_data = state.get("structured_prospect_data", {})
    
    # 1. Fetch Campaign Config to inform the LLM decision
    campaign_config = {}
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Campaign).where(Campaign.id == campaign_id))
        campaign = result.scalars().first()
        if campaign:
            campaign_config = campaign.config
            
    system_prompt = SystemMessage(content="""
    You are an Outreach Strategy Agent. Your job is to determine the best channel to contact this prospect.
    You must output a structured JSON with 'channel' (must be exactly 'email' or 'linkedin') and a brief 'reasoning'.
    Review the Campaign Configuration rules and the Prospect Profile to make your decision.
    """)
    
    user_prompt = HumanMessage(content=f"""
    Campaign Configuration: {campaign_config}
    Prospect Profile: {structured_data}
    """)
    
    import os
    llm = ChatOpenAI(
        model="openai/gpt-oss-20b",
        api_key=os.getenv("GROQ_API_KEY", "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"),
        base_url="https://api.groq.com/openai/v1",
        temperature=0.1
    )
    structured_llm = llm.with_structured_output(StrategyDecision)
    
    decision: StrategyDecision = await structured_llm.ainvoke([system_prompt, user_prompt])
    print(f"Strategy Decision: Route to {decision.channel} - {decision.reasoning}")
    
    # Write to AgentLog
    async with AsyncSessionLocal() as db:
        db.add(AgentLog(
            campaign_id=campaign_id,
            prospect_id=prospect_id,
            agent_name="Strategy Node",
            action="ROUTED_CHANNEL",
            status="SUCCESS",
            prompt_version="v1.0",
            details={"channel": decision.channel, "reasoning": decision.reasoning}
        ))
        await db.commit()
        
    return {"selected_channel": decision.channel}

class EmailDraftResponse(BaseModel):
    subject: str
    body: str

async def email_drafter_node(state: AgentState) -> dict[str, Any]:
    """
    The Email Drafter Node.
    Writes a highly personalized cold email based on the prospect's structured profile
    and the campaign's configuration/value proposition.
    """
    print("--- [Node: Email Drafter] Drafting highly personalized outreach ---")
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    structured_data = state.get("structured_prospect_data", {})
    
    # Assuming campaign value prop is part of the targeting criteria or config, 
    # but for now we'll pass a general directive based on ICP criteria
    icp_criteria = state.get("icp_criteria", {})
    
    # RAG Retrieval: Fetch the most relevant knowledge documents
    knowledge_context = "No specific knowledge base available."
    query = f"Industry: {structured_data.get('industry', '')} Role: {structured_data.get('title', '')}"
    query_vector = embeddings.embed_query(query)
    
    async with AsyncSessionLocal() as db:
        results = await db.execute(
            select(KnowledgeDocument)
            .where(KnowledgeDocument.campaign_id == campaign_id)
            .order_by(KnowledgeDocument.embedding.cosine_distance(query_vector))
            .limit(2)
        )
        knowledge_docs = results.scalars().all()
        if knowledge_docs:
            knowledge_context = "\n\n".join([doc.content for doc in knowledge_docs])
    
    system_prompt = SystemMessage(content="""
    You are an elite B2B SDR. Draft a highly personalized cold email for the given prospect.
    Your email must be concise, engaging, and highlight a clear value proposition related to their industry/role.
    Return a structured JSON with 'subject' and 'body'.
    """)
    
    user_prompt = HumanMessage(content=f"""
    Target Audience/Campaign Context: {icp_criteria}
    Campaign Knowledge Base (Use this for context/case studies):
    {knowledge_context}
    
    Prospect Profile: {structured_data}
    """)
    
    import os
    
    llm = ChatOpenAI(
        model="openai/gpt-oss-20b",
        api_key=os.getenv("GROQ_API_KEY", "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"),
        base_url="https://api.groq.com/openai/v1",
        temperature=0.4
    )
    structured_llm = llm.with_structured_output(EmailDraftResponse, include_raw=True)
    
    response = await structured_llm.ainvoke([system_prompt, user_prompt])
    draft: EmailDraftResponse = response["parsed"]
    raw_msg = response["raw"]
    
    usage = raw_msg.usage_metadata or {}
    
    final_email_text = f"Subject: {draft.subject}\n\n{draft.body}"
    print(f"Drafted Email:\n{final_email_text}")
    
    details = {"subject": draft.subject, "body_preview": draft.body[:100] + "..."}
    if usage:
        details["meta"] = {
            "model": "openai/gpt-oss-20b (Groq)",
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    
    # Update the Database
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            prospect.stage = ProspectStage.DRAFTED
            prospect.draft_email = final_email_text
            
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="Email Personalization Node",
                action="DRAFTED_EMAIL",
                status="SUCCESS",
                prompt_version="v1.0",
                details=details
            ))
            
            await db.commit()
            
    return {
        "messages": [SystemMessage(content=f"Email drafted with subject: {draft.subject}")]
    }

class LinkedinDraftResponse(BaseModel):
    message: str

async def linkedin_drafter_node(state: AgentState) -> dict[str, Any]:
    """
    The LinkedIn Drafter Node.
    Writes a highly personalized, 300-character max LinkedIn connection request.
    """
    print("--- [Node: LinkedIn Drafter] Drafting LinkedIn connection request ---")
    prospect_id = state.get("prospect_id")
    campaign_id = state.get("campaign_id")
    structured_data = state.get("structured_prospect_data", {})
    icp_criteria = state.get("icp_criteria", {})
    
    system_prompt = SystemMessage(content="""
    You are an elite B2B SDR. Draft a highly personalized LinkedIn connection request for the given prospect.
    It must be strictly UNDER 300 characters. Be conversational and mention their industry or role.
    Return a structured JSON with 'message'.
    """)
    
    user_prompt = HumanMessage(content=f"""
    Target Audience: {icp_criteria}
    Prospect Profile: {structured_data}
    """)
    
    import os
    llm = ChatOpenAI(
        model="openai/gpt-oss-20b",
        api_key=os.getenv("GROQ_API_KEY", "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"),
        base_url="https://api.groq.com/openai/v1",
        temperature=0.4
    )
    structured_llm = llm.with_structured_output(LinkedinDraftResponse)
    
    draft: LinkedinDraftResponse = await structured_llm.ainvoke([system_prompt, user_prompt])
    
    final_msg = draft.message
    print(f"Drafted LinkedIn:\n{final_msg}")
    
    # Update Database
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            prospect.stage = ProspectStage.DRAFTED_LINKEDIN
            prospect.draft_linkedin_msg = final_msg
            
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="LinkedIn Personalization Node",
                action="DRAFTED_LINKEDIN",
                status="SUCCESS",
                prompt_version="v1.0",
                details={"message": final_msg}
            ))
            
            await db.commit()
            
    return {
        "messages": [SystemMessage(content="LinkedIn connection request drafted.")]
    }
