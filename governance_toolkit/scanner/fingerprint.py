from __future__ import annotations

import hashlib
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import List, Optional

FRAMEWORK_DISPLAY_NAMES = {
    "anthropic_claude": "Anthropic Claude SDK",
    "langchain": "LangChain",
    "langgraph": "LangGraph",
    "crewai": "CrewAI",
    "autogpt": "AutoGPT",
    "unknown": "Unknown",
}


def make_agent_id(file_path: str, framework: str, line_number: int) -> str:
    raw = f"{file_path}:{framework}:{line_number}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


@dataclass
class AgentFingerprint:
    agent_id: str
    name: str
    file_path: str
    line_number: int
    framework: str
    model: Optional[str]
    tools: List[str]
    owner: Optional[str]
    evidence: List[str]
    scan_timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["scan_timestamp"] = self.scan_timestamp.isoformat()
        d["framework_display"] = FRAMEWORK_DISPLAY_NAMES.get(self.framework, self.framework)
        return d

    def to_agent_create(self) -> dict:
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "framework": self.framework,
            "model": self.model,
            "tools": self.tools,
            "owner": self.owner,
            "file_path": self.file_path,
        }
