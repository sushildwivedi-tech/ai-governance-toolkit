# AI Agent Governance Toolkit

A toolkit for discovering, registering, and scoring autonomous AI agents against the **OWASP LLM 2026 governance maturity scale**.

> "You cannot secure what you cannot see." — OWASP LLM Top 10, June 2026

## The Problem

Organizations deploying AI agents have no inventory of what's running — no owner, no permission boundaries, no audit trail, no kill switch. This toolkit solves agent blindness through automated discovery and governance scoring.

## Features

- **Static Scanner** — scans any Python codebase and detects AI agents via AST + regex analysis
- **Agent Registry** — SQLite-backed store with a REST API for tracking every agent across your org
- **OWASP Scorer** — rates each agent 0–100 against 5 governance criteria with actionable remediation hints
- **Web Dashboard** — browser UI to scan, view, score, and unregister agents
- **CLI** — `scan`, `list`, `score`, `register`, `serve`

## Supported Frameworks

| Framework | Detection Method |
|-----------|-----------------|
| Anthropic Claude SDK | `import anthropic`, `Anthropic()`, `model="claude-*"`, `ANTHROPIC_API_KEY` |
| LangChain | `AgentExecutor`, `create_react_agent`, `@tool`, `ChatAnthropic` |
| LangGraph | `StateGraph`, `add_node`, `set_entry_point` |
| CrewAI | `Crew`, `Agent(role=...)`, `Process.sequential` |
| AutoGPT | `AutoGPT`, `autogpt.*` imports |

## Installation

```bash
git clone https://github.com/sushildwivedi-tech/ai-governance-toolkit.git
cd ai-governance-toolkit
pip install -e .
```

## Quick Start

```bash
# Scan a codebase and register discovered agents
governance scan ./my-project --register

# List all registered agents with governance scores
governance list

# Full OWASP gap report for a specific agent
governance score <agent-id>

# Start the web dashboard at http://127.0.0.1:8000
governance serve
```

## Web Dashboard

Run `governance serve` and open **http://127.0.0.1:8000**

![Dashboard features: summary cards, scan panel, agent table, OWASP score modal]

- **Summary cards** — total agents, average score, agents below 50, framework breakdown
- **Scan panel** — enter any local path to discover agents; auto-register in one click
- **Registry table** — all agents with color-coded scores (green ≥80 / yellow 40–79 / red <40)
- **Score modal** — per-agent OWASP gap report with pass/fail criteria and remediation steps
- **Unregister** — remove agents from the registry with a two-click confirm

## OWASP Governance Scoring

Each agent is scored out of **100** across 5 criteria (20 pts each):

| Criterion | Pass Condition |
|-----------|---------------|
| Agent Owner Assigned | `owner` field is set |
| Data Classification Set | `data_classification` is declared |
| Tool Permissions Scoped | `tools` list has ≥ 1 explicit entry |
| Ethics Review Current | Status is `passed` and review is ≤ 90 days old |
| Audit Logging Configured | `audit_log_configured` is `true` |

**Score bands:**

| Score | Status |
|-------|--------|
| 80–100 | Governance-mature — safe for production |
| 60–79 | Governance-partial — gaps need attention |
| 40–59 | Governance-immature — escalation recommended |
| 0–39 | Governance-absent — must not be in production |

## REST API

Start with `governance serve`, then use the API at **http://127.0.0.1:8000/docs**

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/v1/scan` | Scan a local directory for agents |
| `POST` | `/api/v1/agents` | Register an agent |
| `GET` | `/api/v1/agents` | List agents (filter by framework, score, owner) |
| `GET` | `/api/v1/agents/{id}` | Get one agent |
| `PATCH` | `/api/v1/agents/{id}` | Update agent metadata |
| `DELETE` | `/api/v1/agents/{id}` | Unregister an agent |
| `GET` | `/api/v1/agents/{id}/score` | Full OWASP gap report |
| `GET` | `/api/v1/summary` | Org-wide governance summary |
| `GET` | `/api/v1/health` | Health check |

## CLI Reference

```
governance scan <path>                      Discover agents in a directory
             --register                     Auto-register to local DB
             --json                         Output as JSON
             -o <file>                      Write JSON to file

governance list                             List registered agents
             --min-score <float>            Filter by minimum score
             --framework <name>             Filter by framework
             --owner <email>               Filter by owner
             --json                         Output as JSON

governance score <agent-id>                 Show OWASP gap report
             --json                         Output as JSON

governance register                         Manually register an agent
             --name <name>                  Agent name (required)
             --framework <name>             Framework (required)
             --owner <email>
             --model <model>
             --tools <a,b,c>
             --data-classification <level>
             --risk-tier <tier>
             --ethics-review-status <status>
             --audit-log-configured

governance serve                            Start the web dashboard + API
             --host <host>                  Default: 127.0.0.1
             --port <port>                  Default: 8000
             --reload                       Auto-reload on code changes
```

## Configuration

Set `GOVERNANCE_DB_URL` to use a different database:

```bash
# Default (local SQLite)
governance serve

# Custom path
GOVERNANCE_DB_URL=sqlite:////var/data/governance.db governance serve
```

## Running Tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

47 tests covering the scanner, OWASP scorer, and REST API.

## Project Structure

```
governance_toolkit/
├── cli.py              # Click CLI
├── scanner/
│   ├── detector.py     # AST + regex agent detection
│   └── fingerprint.py  # AgentFingerprint dataclass
├── registry/
│   ├── api.py          # FastAPI endpoints + web dashboard
│   ├── models.py       # SQLAlchemy ORM
│   ├── schemas.py      # Pydantic schemas
│   ├── db.py           # Database engine
│   └── ui.html         # Single-page web dashboard
└── scorer/
    └── owasp.py        # OWASP governance scoring (pure functions)
```

## License

MIT
