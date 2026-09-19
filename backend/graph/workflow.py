from langgraph.graph import StateGraph, START, END
from .state import AgentState
from .nodes import research_node, icp_fitment_node

# 1. Initialize the StateGraph with our strictly typed schema
workflow = StateGraph(AgentState)

# 2. Add the agent nodes to the graph
workflow.add_node("research", research_node)
workflow.add_node("icp_fitment", icp_fitment_node)

# 3. Define the edges (the execution flow)
workflow.add_edge(START, "research")
workflow.add_edge("research", "icp_fitment")
workflow.add_edge("icp_fitment", END)

# 4. Compile the workflow into a runnable application
compiled_workflow = workflow.compile()
