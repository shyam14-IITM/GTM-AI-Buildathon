from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState

def research_node(state: AgentState) -> Dict[str, Any]:
    """
    The Research Node.
    Responsible for taking raw prospect identifiers (e.g., email/linkedin),
    executing search tools (Tavily/Exa), and structuring the data.
    """
    print(f"--- [Node: Research] Extracting data for Prospect ID: {state.get('prospect_id')} ---")
    
    # 1. Format the LLM System Prompt
    system_prompt = SystemMessage(content="""
    You are an expert SDR Researcher. 
    Your job is to search the web and synthesize data into a clean JSON structure 
    including the prospect's background, current company, and recent achievements.
    """)
    
    # Placeholder: In the future, we would do:
    # llm = ChatOpenAI(model="gpt-4o")
    # response = llm.invoke([system_prompt, HumanMessage(content="Raw prospect data...")])
    # structured_data = parse_json(response.content)
    
    # For now, we mock the output to ensure the graph compiles and flows correctly.
    mock_structured_data = {
        "company_name": "Acme Corp",
        "role": "CTO",
        "recent_news": "Just raised Series B funding."
    }
    
    # The dictionary returned here is merged into the LangGraph state.
    return {"structured_prospect_data": mock_structured_data}

def icp_fitment_node(state: AgentState) -> Dict[str, Any]:
    """
    The ICP Fitment Node.
    Evaluates the `structured_prospect_data` against the `icp_criteria` to determine 
    if the prospect is 'Qualified' or 'Rejected'.
    """
    print("--- [Node: ICP Fitment] Evaluating prospect fit ---")
    
    icp_criteria = state.get("icp_criteria", {})
    structured_data = state.get("structured_prospect_data", {})
    
    system_prompt = SystemMessage(content=f"""
    You are an SDR Manager. Compare the prospect data against the target ICP criteria.
    Output ONLY "Qualified" or "Rejected".
    
    ICP Criteria: {icp_criteria}
    Prospect Data: {structured_data}
    """)
    
    # Placeholder LLM execution...
    # llm = ChatOpenAI(model="gpt-4o")
    # decision = llm.invoke([system_prompt]).content.strip()
    
    # Mocking the decision for flow testing
    decision = "Qualified"
    
    return {"current_status": decision}
