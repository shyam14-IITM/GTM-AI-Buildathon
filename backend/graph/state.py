import operator
from typing import TypedDict, Annotated, Dict, Any, List
from langchain_core.messages import AnyMessage

class AgentState(TypedDict):
    """
    The core state object for the SDR LangGraph orchestration.
    This dictionary is passed from node to node as the agents execute the pipeline.
    """
    # Core Identifiers
    campaign_id: str
    prospect_id: str
    
    # Target criteria pulled from the Campaign's JSON config
    icp_criteria: Dict[str, Any]
    
    # Information gathered and synthesized by the Research node
    structured_prospect_data: Dict[str, Any]
    
    # The current funnel decision made by the agents (e.g., Qualified, Rejected)
    current_status: str
    
    # Store dynamic channel routing decision ('email' or 'linkedin')
    selected_channel: str
    
    # Standard LangGraph message history for LLM interactions.
    # The `operator.add` reducer appends new messages to the existing list.
    messages: Annotated[List[AnyMessage], operator.add]
