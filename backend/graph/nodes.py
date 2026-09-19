from typing import Dict, Any, Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.future import select

from .state import AgentState
from database import AsyncSessionLocal
from models import Prospect, ProspectStage

class ICPDecision(BaseModel):
    status: Literal['Qualified', 'Rejected']
    reasoning: str

async def research_node(state: AgentState) -> Dict[str, Any]:
    """
    The Research Node.
    Responsible for taking raw prospect identifiers (e.g., email/linkedin),
    executing search tools (Tavily/Exa), and structuring the data.
    """
    prospect_id = state.get('prospect_id')
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
            await db.commit()
            
    # The dictionary returned here is merged into the LangGraph state.
    return {"structured_prospect_data": mock_structured_data}

async def icp_fitment_node(state: AgentState) -> Dict[str, Any]:
    """
    The ICP Fitment Node.
    Evaluates the `structured_prospect_data` against the `icp_criteria` to determine 
    if the prospect is 'Qualified' or 'Rejected' using ChatOpenAI structured output.
    """
    print("--- [Node: ICP Fitment] Evaluating prospect fit via LLM ---")
    prospect_id = state.get("prospect_id")
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
    
    # Instantiate Gemini LLM and bind structured output
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
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
            await db.commit()
            
    return {
        "current_status": decision.status,
        "messages": [SystemMessage(content=f"ICP Fitment Reasoning: {decision.reasoning}")]
    }
