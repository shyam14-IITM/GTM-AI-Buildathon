from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import research_node, icp_fitment_node, email_drafter_node, strategy_node, linkedin_drafter_node

def should_strategize(state: AgentState):
    if state.get("current_status") == "Qualified":
        return "strategy"
    return END
    
def route_channel(state: AgentState):
    channel = state.get("selected_channel")
    if channel == "email":
        return "email_drafter"
    elif channel == "linkedin":
        return "linkedin_drafter"
    return END

# 1. Initialize the StateGraph with our strictly typed schema
workflow = StateGraph(AgentState)

# 2. Add the agent nodes to the graph
workflow.add_node("research", research_node)
workflow.add_node("icp_fitment", icp_fitment_node)
workflow.add_node("strategy", strategy_node)
workflow.add_node("email_drafter", email_drafter_node)
workflow.add_node("linkedin_drafter", linkedin_drafter_node)

# 3. Define the edges (the execution flow)
workflow.add_edge(START, "research")
workflow.add_edge("research", "icp_fitment")
workflow.add_conditional_edges("icp_fitment", should_strategize)
workflow.add_conditional_edges("strategy", route_channel)
workflow.add_edge("email_drafter", END)
workflow.add_edge("linkedin_drafter", END)

# 4. Compile the workflow into a runnable application
compiled_workflow = workflow.compile()
