"""Shared terminal UI helpers for the Enterprise Agent Framework CLI."""
import json
import re
from typing import Any

from rich import box
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

console = Console()


def clear_screen() -> None:
    """Clear the terminal when supported, keeping each screen focused."""
    try:
        console.clear()
    except Exception:
        pass


def page(title: str, breadcrumb: str | None = None, subtitle: str | None = None) -> None:
    """Render a consistent screen heading."""
    if breadcrumb:
        console.print(f"[dim]{breadcrumb}[/dim]")
    console.print(Panel.fit(
        f"[bold cyan]{title}[/bold cyan]" + (f"\n[dim]{subtitle}[/dim]" if subtitle else ""),
        border_style="cyan",
    ))


def header():
    """Display the framework welcome screen."""
    console.print()
    console.print(Panel.fit(
        "[bold cyan]Build • Manage • Execute[/bold cyan]\n\n"
        "Create and run AI agents, workflows, tools, guardrails, and knowledge bases.",
        title="Enterprise Agent Framework",
        border_style="cyan",
    ))
    console.print()


def menu(title, items, *, breadcrumb: str | None = None, subtitle: str | None = None,
         show_prompt_navigation: bool = False, module_navigation: bool = False):
    """Display a clean, consistent menu."""
    page(title, breadcrumb, subtitle)
    for item in items:
        console.print(f"  {item}")
    if module_navigation:
        console.print()
        console.print("  [dim]B. Back[/dim]")
        console.print("  [dim]0. Exit[/dim]")
    if show_prompt_navigation:
        console.print()
        console.print("[dim]B[/dim] Back   [dim]0[/dim] Exit")
    console.print()


def navigation_footer(*, cancel: bool = False) -> None:
    """Show navigation once for a guided operation rather than beside every field."""
    if cancel:
        console.print("[dim]B[/dim] Back   [dim]0[/dim] Exit")
    else:
        console.print("[dim]B[/dim] Back   [dim]0[/dim] Exit")
    console.print()


def success(message):
    console.print()
    console.print(f"[green]✓ {message}[/green]")
    console.print()


def error(message):
    console.print()
    console.print(f"[red]✗ {message}[/red]")
    console.print()


def info(message):
    console.print()
    console.print(f"[cyan]• {message}[/cyan]")
    console.print()


def render_execution_result(result: Any, title: str = "Execution Result") -> None:
    """Render agent and workflow execution results in a professional, structured table and panel format."""
    console.print()

    # 0. Unwrap result from CrewAI CrewOutput or any wrapper object
    data = result
    if hasattr(result, "json_dict") and isinstance(result.json_dict, dict) and result.json_dict:
        data = result.json_dict
    elif hasattr(result, "raw") and result.raw:
        data = result.raw
    elif hasattr(result, "output") and result.output:
        data = result.output
    elif hasattr(result, "result") and result.result:
        data = result.result

    # 1. Parse JSON if string
    if isinstance(data, str):
        cleaned = re.sub(r"^```(?:json)?\s*", "", data.strip(), flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned).strip()
        try:
            data = json.loads(cleaned)
        except Exception:
            m = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", cleaned)
            if m:
                try:
                    data = json.loads(m.group(1))
                except Exception:
                    pass

    # 2. Recommendations Format (e.g. Fleet Recommendation Agent or any recommendation workflow)
    if isinstance(data, dict) and "recommendations" in data:
        status = str(data.get("recommendation_status", data.get("status", "complete"))).upper()
        recs = data.get("recommendations", [])
        recs_count = len(recs) if isinstance(recs, list) else 0

        console.print(Panel.fit(
            f"[bold green]Status:[/bold green] {status}  •  "
            f"[bold green]Recommendations Generated:[/bold green] {recs_count}",
            title=f"[bold cyan]{title}[/bold cyan]",
            border_style="cyan",
        ))

        # Executive Summary
        if data.get("executive_summary"):
            console.print()
            console.print(Panel(
                data["executive_summary"],
                title="[bold cyan]Executive Summary[/bold cyan]",
                border_style="cyan",
                padding=(1, 2),
            ))

        # Recommendations Table
        if recs and isinstance(recs, list) and isinstance(recs[0], dict):
            console.print()
            rec_table = Table(
                title="[bold green]Fleet Optimization Recommendations[/bold green]",
                box=box.ROUNDED,
                header_style="bold magenta",
                show_lines=True,
                expand=True,
            )
            rec_table.add_column("ID", style="bold cyan", justify="center", no_wrap=True)
            rec_table.add_column("Priority", justify="center", no_wrap=True)
            rec_table.add_column("Category", style="cyan", no_wrap=True)
            rec_table.add_column("Target Device(s)", style="yellow")
            rec_table.add_column("Operational Action", style="bold white")
            rec_table.add_column("Reason & Evidence")
            rec_table.add_column("Confidence", justify="center", no_wrap=True)

            for r in recs:
                if not isinstance(r, dict):
                    continue
                prio = str(r.get("priority", "Medium")).strip()
                if prio.lower() == "high":
                    prio_badge = "[bold red]HIGH[/bold red]"
                elif prio.lower() == "medium":
                    prio_badge = "[bold yellow]MEDIUM[/bold yellow]"
                else:
                    prio_badge = "[bold green]LOW[/bold green]"

                ev = r.get("evidence", {})
                devices = []
                if isinstance(ev, dict):
                    devices = ev.get("device_ids", [])
                    if not devices and "office_ids" in ev:
                        devices = [f"Office {o}" for o in ev["office_ids"]]
                elif isinstance(ev, list):
                    devices = ev
                target_str = ", ".join(str(d) for d in devices) if devices else "Fleet-wide"

                reason_text = str(r.get("reason", ""))
                if isinstance(ev, dict):
                    extra_ev = []
                    if "connectivity_status" in ev:
                        extra_ev.append(f"Connectivity: {ev['connectivity_status']}")
                    if "temperature_c" in ev:
                        extra_ev.append(f"Temp: {ev['temperature_c']}°C")
                    if "health_score" in ev:
                        extra_ev.append(f"Health: {ev['health_score']}")
                    if "maintenance_status" in ev:
                        extra_ev.append(f"Maint: {ev['maintenance_status']}")
                    if extra_ev:
                        reason_text += f"\n[dim]({'; '.join(extra_ev)})[/dim]"

                rec_table.add_row(
                    str(r.get("recommendation_id", "REC")),
                    prio_badge,
                    str(r.get("category", "General")),
                    target_str,
                    str(r.get("action", "")),
                    reason_text,
                    str(r.get("confidence", "Medium")),
                )

            console.print(rec_table)
        elif not recs:
            console.print()
            console.print(Panel(
                "[yellow]No actionable recommendations required or data insufficient. Review report below for details.[/yellow]",
                title="[bold yellow]Recommendations[/bold yellow]",
                border_style="yellow",
            ))

        # Action breakdowns (handling dict, list of dicts, list of strings, or single string)
        action_groups = [
            ("Connectivity Actions", data.get("connectivity_actions")),
            ("Maintenance Actions", data.get("maintenance_actions")),
            ("Warranty Actions", data.get("warranty_actions")),
            ("Supply Actions", data.get("supply_actions")),
            ("Fleet Balancing Opportunities", data.get("fleet_balancing_opportunities")),
        ]

        for group_title, items in action_groups:
            if not items:
                continue
            if isinstance(items, list) and items:
                if isinstance(items[0], dict):
                    act_table = Table(
                        title=f"[bold cyan]{group_title}[/bold cyan]",
                        box=box.SIMPLE_HEAD,
                        show_lines=False,
                        expand=True,
                    )
                    keys = list(items[0].keys())
                    for k in keys:
                        act_table.add_column(
                            k.replace("_", " ").title(),
                            style="bold" if k in ("device_id", "action") else "",
                        )
                    for it in items:
                        if isinstance(it, dict):
                            act_table.add_row(*[str(it.get(k, "")) for k in keys])
                    console.print()
                    console.print(act_table)
                elif isinstance(items[0], str):
                    act_table = Table(
                        title=f"[bold cyan]{group_title}[/bold cyan]",
                        box=box.SIMPLE_HEAD,
                        show_lines=False,
                        expand=True,
                    )
                    act_table.add_column("Action / Recommendation", style="white")
                    for it in items:
                        act_table.add_row(str(it))
                    console.print()
                    console.print(act_table)
            elif isinstance(items, str) and items.strip().lower() not in ("none", "none required", "none required.", "n/a", "[]"):
                console.print()
                console.print(Panel(
                    items,
                    title=f"[bold cyan]{group_title}[/bold cyan]",
                    border_style="cyan",
                ))

        # Additional information required (handling both list of dicts and list of strings)
        add_info = data.get("additional_information_required", [])
        if add_info and isinstance(add_info, list):
            console.print()
            if isinstance(add_info[0], dict):
                info_table = Table(
                    title="[bold yellow]Additional Information Required[/bold yellow]",
                    box=box.ROUNDED,
                    border_style="yellow",
                    expand=True,
                )
                info_table.add_column("Issue", style="bold yellow")
                info_table.add_column("Required Action", style="white")
                info_table.add_column("Missing Evidence", style="dim")
                info_table.add_column("Data Source", style="cyan")
                for it in add_info:
                    if isinstance(it, dict):
                        info_table.add_row(
                            str(it.get("issue", "Issue")),
                            str(it.get("required_action", "")),
                            str(it.get("evidence_missing", "N/A")),
                            str(it.get("data_source", "N/A")),
                        )
                console.print(info_table)
            else:
                info_lines = "\n".join(f"• {item}" for item in add_info)
                console.print(Panel(
                    info_lines,
                    title="[bold yellow]Additional Information Required[/bold yellow]",
                    border_style="yellow",
                ))

        # Markdown report if present
        if data.get("formatted_report"):
            console.print()
            console.print(Panel(
                Markdown(data["formatted_report"]),
                title="[bold cyan]Full Report[/bold cyan]",
                border_style="cyan",
            ))

        console.print()
        return

    # 3. Records Format (e.g. Data Collector Agent or any database query)
    if isinstance(data, dict):
        records_key = None
        for candidate in ("records", "devices", "rows", "items", "data", "results"):
            if candidate in data and isinstance(data[candidate], list) and data[candidate] and isinstance(data[candidate][0], dict):
                records_key = candidate
                break

        if records_key:
            records = data[records_key]
            status_text = data.get("collection_status", data.get("status", "success"))
            console.print(Panel.fit(
                f"[bold green]Status:[/bold green] {str(status_text).upper()}  •  "
                f"[bold green]Records Returned:[/bold green] {len(records)}  •  "
                f"[bold green]Source:[/bold green] {data.get('selected_data_source', data.get('source', 'Database'))}",
                title=f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan",
            ))
            if data.get("summary") or data.get("description"):
                console.print()
                console.print(Panel(
                    str(data.get("summary") or data.get("description")),
                    title="[bold cyan]Summary[/bold cyan]",
                    border_style="cyan",
                ))

            console.print()
            rec_table = Table(
                title=f"[bold green]{records_key.replace('_', ' ').title()}[/bold green]",
                box=box.ROUNDED,
                header_style="bold magenta",
                show_lines=True,
                expand=True,
            )
            preferred_cols = [
                ("device_id", "Device ID"),
                ("office_id", "Office"),
                ("city", "City"),
                ("device_model", "Model"),
                ("fleet_status", "Fleet Status"),
                ("connectivity_status", "Connectivity"),
                ("health_score", "Health"),
                ("toner_level_pct", "Toner %"),
                ("maintenance_status", "Maintenance"),
            ]
            first_row = records[0]
            display_cols = [
                (k, label) for k, label in preferred_cols if k in first_row
            ]
            if not display_cols:
                display_cols = [(k, k.replace("_", " ").title()) for k in list(first_row.keys())[:10]]

            for k, label in display_cols:
                rec_table.add_column(label, style="bold cyan" if k == "device_id" else "")

            for row in records:
                if isinstance(row, dict):
                    rec_table.add_row(*[str(row.get(k, "")) for k, _ in display_cols])

            console.print(rec_table)

            if data.get("formatted_report") or data.get("report"):
                report_text = data.get("formatted_report") or data.get("report")
                console.print()
                console.print(Panel(
                    Markdown(str(report_text)),
                    title="[bold cyan]Report[/bold cyan]",
                    border_style="cyan",
                ))

            console.print()
            return

    # 4. Generic list of dicts (any custom tabular output)
    if isinstance(data, list) and data and isinstance(data[0], dict):
        console.print()
        gen_table = Table(
            title=f"[bold green]{title}[/bold green]",
            box=box.ROUNDED,
            header_style="bold magenta",
            show_lines=True,
            expand=True,
        )
        keys = list(data[0].keys())
        for k in keys:
            gen_table.add_column(k.replace("_", " ").title(), style="bold cyan" if k in ("id", "device_id", "name") else "")
        for item in data:
            if isinstance(item, dict):
                gen_table.add_row(*[str(item.get(k, "")) for k in keys])
        console.print(gen_table)
        console.print()
        return

    # 5. Generic dictionary (clean Key-Value summary and markdown panels)
    if isinstance(data, dict):
        scalars = {k: v for k, v in data.items() if not isinstance(v, (dict, list)) and k not in ("formatted_report", "report")}
        nested_markdown = {k: v for k, v in data.items() if k in ("formatted_report", "report") or (isinstance(v, str) and any(m in v for m in ("# ", "## ", "| ")))}

        if scalars:
            kv_table = Table(
                title=f"[bold cyan]{title}[/bold cyan]",
                box=box.ROUNDED,
                show_lines=True,
                expand=True,
            )
            kv_table.add_column("Field", style="bold cyan", no_wrap=True)
            kv_table.add_column("Value", style="white")
            for k, v in scalars.items():
                kv_table.add_row(k.replace("_", " ").title(), str(v))
            console.print(kv_table)
            console.print()

        for k, v in nested_markdown.items():
            console.print(Panel(
                Markdown(str(v)),
                title=f"[bold cyan]{k.replace('_', ' ').title()}[/bold cyan]",
                border_style="cyan",
            ))
            console.print()

        if scalars or nested_markdown:
            return

    # 6. Formatted Markdown / Text
    if isinstance(data, str):
        if any(marker in data for marker in ("# ", "## ", "| ", "**", "- ")):
            console.print(Panel(
                Markdown(data),
                title=f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan",
            ))
            console.print()
            return
        else:
            console.print(Panel(
                data,
                title=f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan",
            ))
            console.print()
            return

    # 7. Fallback: Pretty printed JSON or string
    if isinstance(data, (dict, list)):
        try:
            formatted_json = json.dumps(data, indent=2)
            console.print(Panel(
                formatted_json,
                title=f"[bold cyan]{title}[/bold cyan]",
                border_style="cyan",
            ))
        except Exception:
            console.print(str(data))
    else:
        console.print(str(data))
    console.print()

