#!/usr/bin/env python3
"""
LogSleuth CLI - Command-line interface for incident investigation.

This CLI allows local testing of LogSleuth tools and demonstrates
the investigation workflow without requiring Agent Builder.

Usage:
    python -m src.cli investigate "checkout-service timeout errors"
    python -m src.cli search --query "Connection refused" --service payment-service
    python -m src.cli errors --time-range 2h
    python -m src.cli trace <trace_id>
"""

import sys
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.markdown import Markdown
from datetime import datetime

console = Console()


def get_client():
    """Get Elasticsearch client with error handling."""
    try:
        from src.utils.elasticsearch_client import get_elasticsearch_client, verify_connection
        client = get_elasticsearch_client()
        return client
    except Exception as e:
        console.print(f"[red]Error connecting to Elasticsearch: {e}[/red]")
        console.print("\nMake sure you have configured your .env file.")
        console.print("See: cp .env.example .env")
        sys.exit(1)


@click.group()
@click.version_option(version="0.1.0", prog_name="LogSleuth")
def cli():
    """LogSleuth - Intelligent Log Incident Investigator

    AI-powered incident investigation for DevOps and SRE teams.
    """
    pass


@cli.command()
@click.argument("incident_description")
@click.option("--time-range", "-t", default="2h", help="Time range to investigate (e.g., 1h, 30m, 2h)")
@click.option("--save/--no-save", default=False, help="Save investigation results")
def investigate(incident_description: str, time_range: str, save: bool):
    """Run a full incident investigation.

    Example:
        logsleuth investigate "checkout-service throwing timeout errors"
    """
    client = get_client()

    console.print(Panel.fit(
        f"[bold blue]LogSleuth Investigation[/bold blue]\n\n"
        f"[yellow]Incident:[/yellow] {incident_description}\n"
        f"[yellow]Time Range:[/yellow] {time_range}",
        title="Starting Investigation"
    ))

    from src.tools import (
        search_logs, get_error_frequency, find_error_traces,
        find_correlated_logs, search_past_incidents, save_investigation
    )

    # Step 1: Search for relevant errors
    console.print("\n[bold cyan]Step 1: Searching for errors...[/bold cyan]")
    search_results = search_logs(
        client,
        search_query=incident_description.split()[0],  # Use first word as keyword
        time_range=time_range,
        log_level="error",
        max_results=20,
    )

    if search_results["total"] == 0:
        console.print("[yellow]No errors found matching the description.[/yellow]")
        # Try broader search
        search_results = search_logs(
            client,
            search_query="*",
            time_range=time_range,
            log_level="error",
            max_results=20,
        )

    console.print(f"Found [green]{search_results['total']}[/green] error logs")

    # Step 2: Analyze error frequency
    console.print("\n[bold cyan]Step 2: Analyzing error patterns...[/bold cyan]")
    error_freq = get_error_frequency(client, time_range=time_range)

    if error_freq["service_breakdown"]:
        table = Table(title="Errors by Service")
        table.add_column("Service", style="cyan")
        table.add_column("Count", justify="right", style="red")
        table.add_column("Error Types", style="yellow")

        for svc in error_freq["service_breakdown"]:
            error_types = ", ".join([et["type"] for et in svc["error_types"][:3]])
            table.add_row(svc["service"], str(svc["error_count"]), error_types)

        console.print(table)

    if error_freq["spike_detected"]:
        console.print(f"\n[red bold]Spike Detected![/red bold]")
        console.print(f"  Time: {error_freq['spike_detected']['timestamp']}")
        console.print(f"  Errors: {error_freq['spike_detected']['error_count']}")
        console.print(f"  Severity: {error_freq['spike_detected']['severity']}")

    # Step 3: Identify root cause service
    root_cause_service = None
    if error_freq["service_breakdown"]:
        # The service with most errors is likely the root cause or most affected
        root_cause_service = error_freq["service_breakdown"][0]["service"]
        console.print(f"\n[bold cyan]Step 3: Tracing errors from {root_cause_service}...[/bold cyan]")

        # Find traces from error logs
        traces = find_error_traces(client, service_name=root_cause_service, time_range=time_range)

        if traces["traces"]:
            console.print(f"Found [green]{traces['traces_found']}[/green] error traces")

            # Trace the first error to find cross-service impact
            trace_id = traces["traces"][0]["trace_id"]
            console.print(f"\nTracing request: {trace_id[:16]}...")

            correlated = find_correlated_logs(client, trace_id)

            if correlated["timeline"]:
                console.print(f"\n[bold]Request Timeline:[/bold]")
                timeline_table = Table()
                timeline_table.add_column("Time", style="dim")
                timeline_table.add_column("Service", style="cyan")
                timeline_table.add_column("Level", style="yellow")
                timeline_table.add_column("Message")

                for entry in correlated["timeline"][:10]:
                    level_style = "red" if entry["level"] == "error" else "yellow" if entry["level"] == "warn" else "green"
                    time_str = entry["timestamp"].split("T")[1][:12] if entry["timestamp"] else ""
                    timeline_table.add_row(
                        time_str,
                        entry["service"],
                        f"[{level_style}]{entry['level'].upper()}[/{level_style}]",
                        entry["message"][:60] + "..." if len(entry["message"]) > 60 else entry["message"]
                    )

                console.print(timeline_table)

                if correlated["root_cause_service"]:
                    root_cause_service = correlated["root_cause_service"]

    # Step 4: Check for similar past incidents
    console.print("\n[bold cyan]Step 4: Checking past incidents...[/bold cyan]")
    past = search_past_incidents(client, search_terms=incident_description)

    if past["total"] > 0:
        console.print(f"Found [green]{past['total']}[/green] similar past incidents")
        for inc in past["incidents"][:2]:
            console.print(f"\n  [bold]{inc['id']}[/bold]")
            console.print(f"  Root cause: {inc['root_cause'][:80]}..." if inc["root_cause"] else "  Root cause: Unknown")
            if inc["resolution"]:
                console.print(f"  Resolution: {inc['resolution'][:80]}...")
    else:
        console.print("[dim]No similar past incidents found.[/dim]")

    # Step 5: Generate summary
    console.print("\n")
    affected_services = [s["service"] for s in error_freq["service_breakdown"]] if error_freq["service_breakdown"] else []

    summary = f"""## Investigation Summary

**Incident**: {incident_description}
**Time Range**: Last {time_range}
**Status**: Root Cause Identified

## Findings

**Total Errors**: {error_freq['total_errors']}
**Root Cause Service**: {root_cause_service or 'Unknown'}
**Affected Services**: {', '.join(affected_services[:5]) or 'None identified'}

## Error Breakdown
"""
    for svc in error_freq["service_breakdown"][:5]:
        error_types = ", ".join([f"{et['type']} ({et['count']})" for et in svc["error_types"][:2]])
        summary += f"- **{svc['service']}**: {svc['error_count']} errors - {error_types}\n"

    if error_freq["spike_detected"]:
        summary += f"""
## Incident Timeline

- **{error_freq['spike_detected']['timestamp']}**: Error spike detected ({error_freq['spike_detected']['error_count']} errors)
"""

    summary += """
## Recommended Actions

1. Review error logs from the root cause service
2. Check recent deployments or configuration changes
3. Verify database and external service connectivity
4. Consider enabling circuit breakers if not already active
"""

    console.print(Panel(Markdown(summary), title="Investigation Report", border_style="green"))

    # Save if requested
    if save and root_cause_service:
        console.print("\n[bold cyan]Saving investigation...[/bold cyan]")
        now = datetime.utcnow().isoformat()
        result = save_investigation(
            client,
            incident_input=incident_description,
            time_range_start=now,
            time_range_end=now,
            root_cause=f"Errors originated in {root_cause_service}",
            root_cause_service=root_cause_service,
            affected_services=affected_services,
            error_types=[et["type"] for svc in error_freq["service_breakdown"][:3] for et in svc["error_types"][:2]],
            error_count=int(error_freq["total_errors"]),
        )
        console.print(f"[green]Saved as: {result['investigation_id']}[/green]")


@cli.command()
@click.option("--query", "-q", required=True, help="Search term")
@click.option("--service", "-s", default=None, help="Filter by service name")
@click.option("--level", "-l", default=None, type=click.Choice(["error", "warn", "info", "debug"]))
@click.option("--time-range", "-t", default="1h", help="Time range (e.g., 1h, 30m)")
@click.option("--limit", "-n", default=20, help="Max results")
def search(query: str, service: str, level: str, time_range: str, limit: int):
    """Search logs by keyword."""
    client = get_client()

    from src.tools import search_logs

    results = search_logs(
        client,
        search_query=query,
        time_range=time_range,
        service_name=service,
        log_level=level,
        max_results=limit,
    )

    console.print(f"\nFound [green]{results['total']}[/green] logs matching '{query}'\n")

    if results["hits"]:
        table = Table()
        table.add_column("Time", style="dim", width=12)
        table.add_column("Service", style="cyan", width=18)
        table.add_column("Level", width=6)
        table.add_column("Message")

        for hit in results["hits"]:
            level_style = "red" if hit["level"] == "error" else "yellow" if hit["level"] == "warn" else "green"
            time_str = hit["timestamp"].split("T")[1][:12] if hit["timestamp"] else ""
            table.add_row(
                time_str,
                hit["service"] or "",
                f"[{level_style}]{hit['level'].upper()}[/{level_style}]",
                hit["message"][:70] + "..." if len(hit["message"]) > 70 else hit["message"]
            )

        console.print(table)


@cli.command()
@click.option("--time-range", "-t", default="1h", help="Time range (e.g., 1h, 30m)")
@click.option("--service", "-s", default=None, help="Filter by service name")
def errors(time_range: str, service: str):
    """Show error frequency and patterns."""
    client = get_client()

    from src.tools import get_error_frequency

    results = get_error_frequency(
        client,
        time_range=time_range,
        service_name=service,
    )

    console.print(f"\n[bold]Error Analysis[/bold] (last {time_range})")
    console.print(f"Total errors: [red]{results['total_errors']}[/red]\n")

    if results["service_breakdown"]:
        table = Table(title="Errors by Service")
        table.add_column("Service", style="cyan")
        table.add_column("Count", justify="right", style="red")
        table.add_column("Error Types")

        for svc in results["service_breakdown"]:
            types = ", ".join([f"{et['type']} ({et['count']})" for et in svc["error_types"][:3]])
            table.add_row(svc["service"], str(svc["error_count"]), types)

        console.print(table)

    if results["spike_detected"]:
        console.print(f"\n[red bold]Spike Detected![/red bold]")
        console.print(f"  Time: {results['spike_detected']['timestamp']}")
        console.print(f"  Count: {results['spike_detected']['error_count']}")


@cli.command()
@click.argument("trace_id")
def trace(trace_id: str):
    """Trace a request across services by trace_id."""
    client = get_client()

    from src.tools import find_correlated_logs

    results = find_correlated_logs(client, trace_id)

    console.print(f"\n[bold]Trace: {trace_id}[/bold]")
    console.print(f"Services: {', '.join(results['services_involved'])}")
    console.print(f"Has errors: {'Yes' if results['has_errors'] else 'No'}")

    if results["root_cause_service"]:
        console.print(f"Root cause service: [red]{results['root_cause_service']}[/red]")

    if results["timeline"]:
        console.print("\n[bold]Timeline:[/bold]")
        table = Table()
        table.add_column("Time", style="dim", width=15)
        table.add_column("Service", style="cyan", width=18)
        table.add_column("Level", width=6)
        table.add_column("Message")

        for entry in results["timeline"]:
            level = entry.get("level", "info")
            level_style = "red" if level == "error" else "yellow" if level == "warn" else "green"
            time_str = entry["timestamp"].split("T")[1][:15] if entry.get("timestamp") else ""
            table.add_row(
                time_str,
                entry["service"],
                f"[{level_style}]{level.upper()}[/{level_style}]",
                entry["message"][:60] + "..." if len(entry["message"]) > 60 else entry["message"]
            )

        console.print(table)


@cli.command()
@click.option("--query", "-q", required=True, help="Search terms")
def history(query: str):
    """Search past investigations."""
    client = get_client()

    from src.tools import search_past_incidents

    results = search_past_incidents(client, search_terms=query)

    console.print(f"\nFound [green]{results['total']}[/green] past incidents matching '{query}'\n")

    for inc in results["incidents"]:
        console.print(Panel(
            f"[bold]Root Cause:[/bold] {inc['root_cause'] or 'Unknown'}\n\n"
            f"[bold]Services:[/bold] {', '.join(inc['affected_services'])}\n\n"
            f"[bold]Resolution:[/bold] {inc['resolution'] or 'Not recorded'}",
            title=f"{inc['id']} - {inc['timestamp'][:10] if inc['timestamp'] else 'Unknown date'}",
            border_style="blue"
        ))


@cli.command()
def status():
    """Check connection status and data availability."""
    client = get_client()

    from src.utils.elasticsearch_client import verify_connection, LOG_INDEX, INVESTIGATION_INDEX

    console.print("[bold]LogSleuth Status[/bold]\n")

    # Check connection
    try:
        verify_connection(client)
        console.print("[green]Elasticsearch: Connected[/green]")
    except Exception as e:
        console.print(f"[red]Elasticsearch: Error - {e}[/red]")
        return

    # Check indices
    if client.indices.exists(index=LOG_INDEX):
        count = client.count(index=LOG_INDEX)["count"]
        console.print(f"[green]Log index ({LOG_INDEX}): {count} documents[/green]")
    else:
        console.print(f"[yellow]Log index ({LOG_INDEX}): Not found[/yellow]")

    if client.indices.exists(index=INVESTIGATION_INDEX):
        count = client.count(index=INVESTIGATION_INDEX)["count"]
        console.print(f"[green]Investigation index ({INVESTIGATION_INDEX}): {count} documents[/green]")
    else:
        console.print(f"[dim]Investigation index ({INVESTIGATION_INDEX}): Not found (will be created on first save)[/dim]")


if __name__ == "__main__":
    cli()
