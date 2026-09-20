from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import (
    research_node, icp_fitment_node, email_drafter_node, 
    strategy_node, linkedin_drafter_node, email_sender_node, 
    conversation_node, voice_node, follow_up_node
)

def route_entry(state: AgentState):
    status = state.get("current_status")
    if status == "Discovered":
        config = state.get("campaign_config", {})
        if config.get("is_research_enabled", True):
            return "research"
        return "icp_fitment"
    elif status == "Contacted":
        config = state.get("campaign_config", {})
        if config.get("is_follow_up_enabled"):
            return "follow_up"
        return END
    return END

def should_strategize(state: AgentState):
    if state.get("current_status") == "Qualified":
        return "strategy"
    return END
    
def route_channel(state: AgentState):
    # Strategy node already safely picked a channel from the enabled list
    channel = state.get("selected_channel")
    if channel == "email":
        return "email_drafter"
    elif channel == "linkedin":
        return "linkedin_drafter"
    elif channel == "voice":
        return "voice_node"
    return END

# 1. Initialize the StateGraph with our strictly typed schema
workflow = StateGraph(AgentState)

# 2. Add the agent nodes to the graph
workflow.add_node("research", research_node)
workflow.add_node("icp_fitment", icp_fitment_node)
workflow.add_node("strategy", strategy_node)
workflow.add_node("email_drafter", email_drafter_node)
workflow.add_node("email_sender", email_sender_node)
workflow.add_node("linkedin_drafter", linkedin_drafter_node)
workflow.add_node("voice_node", voice_node)
workflow.add_node("follow_up", follow_up_node)

# 3. Define the edges (the execution flow)
workflow.add_conditional_edges(START, route_entry)
workflow.add_edge("research", "icp_fitment")
workflow.add_conditional_edges("icp_fitment", should_strategize)
workflow.add_conditional_edges("strategy", route_channel)
workflow.add_edge("email_drafter", "email_sender")
workflow.add_edge("email_sender", END)
workflow.add_edge("linkedin_drafter", END)
workflow.add_edge("voice_node", END)
workflow.add_edge("follow_up", END)

# 4. Compile the workflow into a runnable application
compiled_workflow = workflow.compile()
