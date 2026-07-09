"""Sample LangGraph agent for scanner testing."""
from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


@tool
def fetch_data(source: str) -> str:
    """Fetch data from a source."""
    return f"Data from {source}"


def call_model(state: AgentState) -> AgentState:
    return state


def should_continue(state: AgentState) -> str:
    return END


workflow = StateGraph(AgentState)
workflow.add_node("agent", call_model)
workflow.set_entry_point("agent")
workflow.add_edge("agent", END)

graph_agent = workflow.compile()
