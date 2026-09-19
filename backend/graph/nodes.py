from typing import Any, Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.future import select

from .state import AgentState
from database import AsyncSessionLocal
from models import Prospect, ProspectStage, AgentLog

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
    
    # 1. Format a realistic synthetic JSON profile
    mock_structured_data = {
        "name": "Jane Doe",
        "title": "CTO",
        "company_size": "200-500",
        "industry": "B2B SaaS"
    }
    
    # 2. Update the Database using SQLAlchemy
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Prospect).where(Prospect.id == prospect_id))
        prospect = result.scalars().first()
        if prospect:
            prospect.stage = ProspectStage.RESEARCHED
            prospect.enriched_data = mock_structured_data
            
            # 3. Write to AgentLog
            db.add(AgentLog(
                campaign_id=campaign_id,
                prospect_id=prospect_id,
                agent_name="Research Node",
                action="ENRICHED",
                status="SUCCESS",
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
    
    # Instantiate Gemini 3.6 Flash and bind structured output
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0)
    structured_llm = llm.with_structured_output(ICPDecision)
    
    # Invoke asynchronously
    decision: ICPDecision = await structured_llm.ainvoke([system_prompt, user_prompt])
    print(f"LLM Decision: {decision.status} - {decision.reasoning}")
    
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
                details={"status": decision.status, "reasoning": decision.reasoning}
            ))
            
            await db.commit()
            
    return {
        "current_status": decision.status,
        "messages": [SystemMessage(content=f"ICP Fitment Reasoning: {decision.reasoning}")]
    }

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
    
    system_prompt = SystemMessage(content="""
    You are an elite B2B SDR. Draft a highly personalized cold email for the given prospect.
    Your email must be concise, engaging, and highlight a clear value proposition related to their industry/role.
    Return a structured JSON with 'subject' and 'body'.
    """)
    
    user_prompt = HumanMessage(content=f"""
    Target Audience/Campaign Context: {icp_criteria}
    Prospect Profile: {structured_data}
    """)
    
    llm = ChatGoogleGenerativeAI(model="gemini-3.6-flash", temperature=0.4)
    structured_llm = llm.with_structured_output(EmailDraftResponse)
    
    draft: EmailDraftResponse = await structured_llm.ainvoke([system_prompt, user_prompt])
    
    final_email_text = f"Subject: {draft.subject}\n\n{draft.body}"
    print(f"Drafted Email:\n{final_email_text}")
    
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
                details={"subject": draft.subject, "body_preview": draft.body[:100] + "..."}
            ))
            
            await db.commit()
            
    return {
        "current_status": "Drafted",
        "messages": [SystemMessage(content=f"Email drafted successfully: {draft.subject}")]
    }
