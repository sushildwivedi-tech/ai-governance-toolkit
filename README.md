# AI Agent Governance Toolkit

A toolkit for discovering, registering, and scoring autonomous AI agents against the **OWASP LLM 2026 governance maturity scale**.

> "You cannot secure what you cannot see." — OWASP LLM Top 10, June 2026

## The Problem

Organizations deploying AI agents have no inventory of what's running — no owner, no permission boundaries, no audit trail, no kill switch. This toolkit solves agent blindness through automated discovery and governance scoring.

## Features

- **Static Scanner** — scans any Python codebase and detects AI agents via AST + regex analysis
- **Agent Registry** — SQLite-backed store with a REST API for tracking every agent across your org
- **OWASP Scorer** — rates each agent 0–100 against 5 governance criteria with actionable remediation hints
- **Agent Register** — a post-deployment accountability inventory: who owns each agent, whether it has its own identity, and whether its actions are logged, rolled up into a green/amber/red traceability status
- **Web Dashboard** — browser UI to scan, view, score, and unregister agents
- **Shift-Left Design Gate** — a design-kickoff risk questionnaire that scores an agent *before* it's built, not after
- **CLI** — `scan`, `list`, `score`, `register`, `seed-register`, `serve`

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

The dashboard has three tabs:

### Pre-Build — Design Gate

A six-question risk gate for use at **design kickoff, before an agent is built** — the scanner and registry catch agents after they exist, this catches the risk before they do. Answer questions about autonomy, tool access, data sensitivity, reversibility, memory, and runtime oversight; it scores the agent and returns a risk tier (Supervised / Semi-autonomous / Fully autonomous) with the design-time controls to build in from day one. Tiers are adapted from the OWASP GenAI Security Project's *State of Agentic AI Security and Governance* report. (`/design-gate` redirects here.)

### Post-Build — Scan & Registry

![Dashboard features: summary cards, scan panel, agent table, OWASP score modal]

- **Summary cards** — total agents, average score, agents below 50, framework breakdown
- **Scan panel** — enter any local path to discover agents; auto-register in one click
- **Registry table** — all agents with color-coded scores (green ≥80 / yellow 40–79 / red <40)
- **Score modal** — per-agent OWASP gap report with pass/fail criteria and remediation steps
- **Unregister** — remove agents from the registry with a two-click confirm

### Agent Register — Accountability

> "Can you name every agent in your organisation right now, and who each one answers to?"

**Identity is the first control for agentic AI.** Only ~28% of organisations (Cloud Security Alliance) can trace an agent's action back to an accountable human — and every other control (human-in-the-loop, audit trails, evaluations) assumes you already know which agent acted and under whose authority.

The Agent Register is a **post-deployment inventory** of your deployed agents. It is a **register, not an IAM system** — it stores **metadata only** and never holds credentials, secrets or tokens (only descriptive fields about them, with a note in the UI beside those fields).

Each record captures:

- **Basics** — name, description, vendor/system, environment (prod/staging/dev), deployment date, status (active/paused/retired)
- **Accountable owner** — a named human with role and contact; agents with **no owner are flagged** in the table
- **Identity** — whether the agent has its own unique identity (vs. a shared or human account), the identity provider/type, a credential-scope summary, and the last rotation date
- **Autonomy & risk** — autonomy level (suggest-only / act-with-approval / act-autonomously), risk tier (low/medium/high/critical), and the permitted actions/systems it can touch
- **Audit** — whether action logging is in place (yes/no/partial), where logs live, last review date, and timestamped audit notes

**Traceability status** is **derived automatically**, never set by hand:

| Status | Condition |
|--------|-----------|
| 🟢 green | Accountable owner **and** unique identity **and** action logging |
| 🟡 amber | One of the three missing |
| 🔴 red | Two or more missing |

The overview shows total agents, % with an accountable owner, % with a unique identity, % with action logging, and the count of red-status agents. The table is filterable (environment, risk tier, traceability status, owner), sortable and searchable.

**Reporting:** export the full register as **CSV**, or open a **board-ready one-page summary** as a print/PDF view. A **Governance mapping** drawer maps the register's fields to the ASD / cyber.gov.au joint guidance, [*Careful adoption of agentic AI*](https://www.cyber.gov.au/business-government/secure-design/artificial-intelligence/careful-adoption-of-agentic-ai-services) (incremental adoption, constrained permissions, low-risk tasks, logging).

The register ships with **10 demo agents** (seeded on first run) so the dashboard demonstrates immediately. Reseed a fresh database at any time with `governance seed-register`.

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
| `POST` | `/api/v1/register/agents` | Add an agent to the accountability register |
| `GET` | `/api/v1/register/agents` | List register agents (filter by environment, risk_tier, status, owner, traceability) |
| `GET` | `/api/v1/register/agents/{id}` | Get one register agent |
| `PATCH` | `/api/v1/register/agents/{id}` | Update a register agent (traceability re-derived) |
| `DELETE` | `/api/v1/register/agents/{id}` | Remove an agent from the register |
| `GET` | `/api/v1/register/summary` | Accountability/traceability summary |
| `GET` | `/api/v1/register/export.csv` | Export the register as CSV |

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

governance seed-register                    Seed the Agent Register with 10 demo agents
                                            (skips if the register already has agents)

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

68 tests covering the scanner, OWASP scorer, traceability logic, and REST API (registry + register).

## Project Structure

```
governance_toolkit/
├── cli.py              # Click CLI
├── scanner/
│   ├── detector.py     # AST + regex agent detection
│   └── fingerprint.py  # AgentFingerprint dataclass
├── registry/
│   ├── api.py          # FastAPI endpoints + web dashboard
│   ├── models.py       # SQLAlchemy ORM (AgentRecord + RegisteredAgent)
│   ├── schemas.py      # Pydantic schemas
│   ├── seed.py         # Demo seed data for the Agent Register
│   ├── db.py           # Database engine
│   └── ui.html         # Single-page web dashboard (3 tabs)
└── scorer/
    ├── owasp.py        # OWASP governance scoring (pure functions)
    └── traceability.py # Agent Register traceability status (pure functions)
```

## License

MIT
