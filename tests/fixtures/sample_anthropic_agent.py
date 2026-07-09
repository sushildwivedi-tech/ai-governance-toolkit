"""Sample Anthropic Claude SDK agent for scanner testing."""
import os
import anthropic
from anthropic import Anthropic, AsyncAnthropic

client = Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))


def search_kb(query: str) -> str:
    """Search the knowledge base."""
    return f"Results for: {query}"


def create_ticket(title: str, description: str) -> dict:
    """Create a support ticket."""
    return {"id": "TICKET-001", "title": title}


def send_email(to: str, subject: str, body: str) -> bool:
    """Send an email notification."""
    return True


def run_support_agent(user_message: str) -> str:
    tools = [
        {"name": "search_kb", "description": "Search knowledge base", "input_schema": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}},
        {"name": "create_ticket", "description": "Create a ticket", "input_schema": {"type": "object", "properties": {"title": {"type": "string"}, "description": {"type": "string"}}, "required": ["title", "description"]}},
    ]

    response = client.messages.create(
        model="claude-opus-4-5",
        max_tokens=1024,
        tools=tools,
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text if response.content else ""


customer_support_agent = run_support_agent
