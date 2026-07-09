"""Sample LangChain agent for scanner testing."""
from langchain.agents import AgentExecutor, create_react_agent
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI


@tool
def search_web(query: str) -> str:
    """Search the web for information."""
    return f"Web results for: {query}"


@tool
def calculator(expression: str) -> str:
    """Evaluate a mathematical expression."""
    return str(eval(expression))


llm = ChatOpenAI(model="gpt-4o", temperature=0)

tools = [search_web, calculator]

agent = create_react_agent(llm, tools, prompt=None)
agent_executor = AgentExecutor(agent=agent, tools=tools, verbose=True)
