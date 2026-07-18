from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

console = Console()


def _score_color(score: float) -> str:
    if score >= 80:
        return "green"
    if score >= 40:
        return "yellow"
    return "red"


def _render_scan_table(fingerprints):
    table = Table(title="Discovered AI Agents", box=box.ROUNDED, show_lines=True)
    table.add_column("File", style="cyan", no_wrap=False, max_width=40)
    table.add_column("Framework", style="magenta")
    table.add_column("Agent Name", style="bold")
    table.add_column("Model", style="blue")
    table.add_column("Tools", style="dim")
    table.add_column("Owner", style="green")

    for fp in fingerprints:
        from governance_toolkit.scanner.fingerprint import FRAMEWORK_DISPLAY_NAMES
        tools_str = ", ".join(fp.tools[:3]) + ("..." if len(fp.tools) > 3 else "") if fp.tools else "-"
        table.add_row(
            Path(fp.file_path).name,
            FRAMEWORK_DISPLAY_NAMES.get(fp.framework, fp.framework),
            fp.name,
            fp.model or "-",
            tools_str,
            fp.owner or "-",
        )

    console.print(table)
    console.print(f"\n[bold]Found {len(fingerprints)} agent(s)[/bold]")


def _render_agents_table(agents):
    table = Table(title="Registered AI Agents", box=box.ROUNDED, show_lines=True)
    table.add_column("Agent ID", style="dim", max_width=12)
    table.add_column("Name", style="bold")
    table.add_column("Framework", style="magenta")
    table.add_column("Owner", style="cyan")
    table.add_column("Score", justify="right")
    table.add_column("Last Seen", style="dim")

    for a in agents:
        score = a.governance_score
        color = _score_color(score)
        table.add_row(
            a.agent_id[:12],
            a.name,
            a.framework,
            a.owner or "-",
            f"[{color}]{score:.0f}/100[/{color}]",
            str(a.last_seen)[:16] if a.last_seen else "-",
        )

    console.print(table)
    console.print(f"\n[bold]{len(agents)} agent(s) registered[/bold]")


def _render_score_report(report):
    score = report.total_score
    color = _score_color(score)

    console.print(Panel(
        f"[{color}][bold]{score:.0f} / {report.max_score}[/bold][/{color}]\n{report.risk_summary}",
        title=f"Governance Score — {report.agent_name}",
        border_style=color,
    ))

    table = Table(box=box.SIMPLE, show_header=True)
    table.add_column("Criterion")
    table.add_column("Status", justify="center")
    table.add_column("Points", justify="right")
    table.add_column("Remediation", style="dim", max_width=50)

    for c in report.criteria:
        status = "[green]✓[/green]" if c.passed else "[red]✗[/red]"
        pts = f"[green]{c.points_earned}[/green]" if c.passed else f"[red]{c.points_earned}[/red]"
        table.add_row(c.label, status, f"{pts}/{c.points_possible}", c.remediation or "")

    console.print(table)

    if report.recommendations:
        console.print("\n[bold yellow]Recommendations:[/bold yellow]")
        for i, rec in enumerate(report.recommendations, 1):
            console.print(f"  {i}. {rec}")


@click.group()
@click.option(
    "--db-url",
    envvar="GOVERNANCE_DB_URL",
    default="sqlite:///./governance.db",
    help="SQLAlchemy database URL",
    show_default=True,
)
@click.pass_context
def cli(ctx, db_url):
    """AI Agent Governance Toolkit — discover, register, and score AI agents."""
    ctx.ensure_object(dict)
    ctx.obj["db_url"] = db_url
    os.environ["GOVERNANCE_DB_URL"] = db_url


@cli.command("scan")
@click.argument("path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--register", is_flag=True, help="Auto-register discovered agents to local registry")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--output", "-o", type=click.Path(), help="Write JSON output to file")
@click.pass_context
def scan(ctx, path, register, output_json, output):
    """Scan a directory for AI agents."""
    from governance_toolkit.scanner import scan_directory
    from governance_toolkit.registry.db import get_db, init_db, reset_engine

    reset_engine()

    fingerprints = scan_directory(Path(path))

    if not fingerprints:
        console.print("[yellow]No AI agents detected.[/yellow]")
        return

    if register:
        init_db()
        db = next(get_db())
        registered = 0
        updated = 0
        from governance_toolkit.registry.models import AgentRecord
        from governance_toolkit.scorer.owasp import calculate_score
        from governance_toolkit.registry.schemas import AgentCreate
        import datetime

        for fp in fingerprints:
            data = fp.to_agent_create()
            existing = db.query(AgentRecord).filter_by(agent_id=fp.agent_id).first()
            if existing:
                existing.last_seen = datetime.datetime.utcnow()
                db.commit()
                updated += 1
            else:
                ac = AgentCreate(**data)
                score = calculate_score(ac)
                now = datetime.datetime.utcnow()
                record = AgentRecord(governance_score=score, first_seen=now, last_seen=now, **data)
                db.add(record)
                db.commit()
                registered += 1

        console.print(f"[green]Registered {registered} new agent(s), updated {updated}.[/green]")

    data = [fp.to_dict() for fp in fingerprints]

    if output:
        Path(output).write_text(json.dumps(data, indent=2, default=str))
        console.print(f"[green]Written to {output}[/green]")
    elif output_json:
        click.echo(json.dumps(data, indent=2, default=str))
    else:
        _render_scan_table(fingerprints)


@cli.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.option("--min-score", type=float, default=0.0, help="Minimum governance score")
@click.option("--framework", default=None, help="Filter by framework")
@click.option("--owner", default=None, help="Filter by owner")
@click.pass_context
def list_agents(ctx, output_json, min_score, framework, owner):
    """List all registered agents with governance scores."""
    from governance_toolkit.registry.db import get_db, init_db, reset_engine
    from governance_toolkit.registry.models import AgentRecord
    from governance_toolkit.registry.schemas import AgentResponse

    reset_engine()
    init_db()
    db = next(get_db())

    q = db.query(AgentRecord)
    if framework:
        q = q.filter_by(framework=framework)
    if owner:
        q = q.filter_by(owner=owner)
    q = q.filter(AgentRecord.governance_score >= min_score)
    agents = q.order_by(AgentRecord.last_seen.desc()).all()

    if not agents:
        console.print("[yellow]No agents registered yet. Run 'governance scan <path> --register' first.[/yellow]")
        return

    if output_json:
        click.echo(json.dumps(
            [AgentResponse.from_orm(a).dict() for a in agents],
            indent=2,
            default=str,
        ))
    else:
        _render_agents_table(agents)


@cli.command("score")
@click.argument("agent_id")
@click.option("--json", "output_json", is_flag=True, help="Output as JSON")
@click.pass_context
def score(ctx, agent_id, output_json):
    """Show full OWASP governance gap report for an agent."""
    from governance_toolkit.registry.db import get_db, init_db, reset_engine
    from governance_toolkit.registry.models import AgentRecord
    from governance_toolkit.registry.schemas import AgentResponse
    from governance_toolkit.scorer.owasp import generate_report

    reset_engine()
    init_db()
    db = next(get_db())

    record = db.query(AgentRecord).filter_by(agent_id=agent_id).first()
    if not record:
        console.print(f"[red]Agent '{agent_id}' not found.[/red]")
        sys.exit(1)

    agent = AgentResponse.from_orm(record)
    report = generate_report(agent)

    if output_json:
        click.echo(report.json(indent=2))
    else:
        _render_score_report(report)


@cli.command("register")
@click.option("--name", required=True, help="Agent name")
@click.option("--framework", required=True,
              type=click.Choice(["anthropic_claude", "langchain", "langgraph", "crewai", "autogpt", "unknown"]),
              help="Agent framework")
@click.option("--owner", default=None, help="Owner email or username")
@click.option("--model", default=None, help="Model name (e.g. claude-opus-4-5)")
@click.option("--tools", default=None, help="Comma-separated list of tool names")
@click.option("--data-classification", default=None,
              type=click.Choice(["public", "internal", "confidential", "restricted"]))
@click.option("--risk-tier", default=None,
              type=click.Choice(["low", "medium", "high", "critical"]))
@click.option("--ethics-review-status", default=None,
              type=click.Choice(["pending", "in_review", "passed", "failed", "not_required"]))
@click.option("--audit-log-configured", is_flag=True, default=False)
@click.pass_context
def register(ctx, name, framework, owner, model, tools, data_classification,
             risk_tier, ethics_review_status, audit_log_configured):
    """Manually register an AI agent."""
    from governance_toolkit.registry.db import get_db, init_db, reset_engine
    from governance_toolkit.registry.models import AgentRecord
    from governance_toolkit.registry.schemas import AgentCreate, AgentResponse
    from governance_toolkit.scorer.owasp import calculate_score
    import datetime
    import hashlib

    reset_engine()
    init_db()
    db = next(get_db())

    tools_list = [t.strip() for t in tools.split(",")] if tools else None
    raw = f"{name}:{framework}"
    agent_id = hashlib.sha256(raw.encode()).hexdigest()[:32]

    existing = db.query(AgentRecord).filter_by(agent_id=agent_id).first()
    if existing:
        console.print(f"[yellow]Agent '{name}' already registered with ID {agent_id}.[/yellow]")
        return

    ac = AgentCreate(
        agent_id=agent_id,
        name=name,
        framework=framework,
        owner=owner,
        model=model,
        tools=tools_list,
        data_classification=data_classification,
        risk_tier=risk_tier,
        ethics_review_status=ethics_review_status,
        audit_log_configured=audit_log_configured,
    )
    score = calculate_score(ac)
    now = datetime.datetime.utcnow()
    data = ac.dict(exclude_none=True)
    data.pop("agent_id", None)
    record = AgentRecord(agent_id=agent_id, governance_score=score, first_seen=now, last_seen=now, **data)
    db.add(record)
    db.commit()
    db.refresh(record)

    console.print(f"[green]Registered agent '{name}' (ID: {agent_id}, Score: {score:.0f}/100)[/green]")


@cli.command("seed-register")
@click.pass_context
def seed_register_cmd(ctx):
    """Seed the Agent Register with demo agents (skips if not empty)."""
    from governance_toolkit.registry.db import get_db, init_db, reset_engine
    from governance_toolkit.registry.seed import seed_register

    reset_engine()
    init_db()
    db = next(get_db())
    inserted = seed_register(db)
    if inserted:
        console.print(f"[green]Seeded {inserted} demo agent(s) into the register.[/green]")
    else:
        console.print("[yellow]Register already has agents — nothing seeded.[/yellow]")


@cli.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8000, show_default=True)
@click.option("--reload", is_flag=True, help="Auto-reload on code changes")
@click.pass_context
def serve(ctx, host, port, reload):
    """Start the governance registry REST API server."""
    import uvicorn
    console.print(f"[green]Starting governance registry on http://{host}:{port}[/green]")
    console.print(f"[dim]API docs: http://{host}:{port}/docs[/dim]")
    uvicorn.run(
        "governance_toolkit.registry.api:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
