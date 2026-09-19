from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import research_node, icp_fitment_node, email_drafter_node

def should_draft_email(state: AgentState):
    if state.get("current_status") == "Qualified":
        return "email_drafter"
    return END

# 1. Initialize the StateGraph with our strictly typed schema
workflow = StateGraph(AgentState)

# 2. Add the agent nodes to the graph
workflow.add_node("research", research_node)
workflow.add_node("icp_fitment", icp_fitment_node)
workflow.add_node("email_drafter", email_drafter_node)

# 3. Define the edges (the execution flow)
workflow.add_edge(START, "research")
workflow.add_edge("research", "icp_fitment")
workflow.add_conditional_edges("icp_fitment", should_draft_email)
workflow.add_edge("email_drafter", END)

# 4. Compile the workflow into a runnable application
compiled_workflow = workflow.compile()
