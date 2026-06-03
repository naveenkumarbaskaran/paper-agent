"""Command-line interface for paper-agent-ai."""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


def _make_agent(api_key: str | None) -> "PaperAgent":
    from paper_agent.agent import PaperAgent

    return PaperAgent(api_key=api_key)


@click.group()
@click.version_option(package_name="paper-agent-ai")
def cli() -> None:
    """paper-agent — AI-powered academic paper analysis using Claude."""


@cli.command("analyze")
@click.argument("source", metavar="<paper.pdf | arxiv_id>")
@click.option(
    "-o",
    "--output",
    "output_path",
    default=None,
    metavar="FILE",
    help="Write the summary to FILE (e.g. summary.md).",
)
@click.option(
    "--api-key",
    envvar="ANTHROPIC_API_KEY",
    default=None,
    help="Anthropic API key (defaults to ANTHROPIC_API_KEY env var).",
)
def analyze_cmd(source: str, output_path: str | None, api_key: str | None) -> None:
    """Analyse a single paper.

    SOURCE can be a local PDF file path or an arXiv paper ID
    (e.g. '2301.07041').

    \b
    Examples:
      paper-agent analyze paper.pdf --output summary.md
      paper-agent analyze 2301.07041
      paper-agent analyze 2301.07041 -o my_summary.md
    """
    agent = _make_agent(api_key)

    label = Path(source).name if source.endswith(".pdf") else f"arXiv:{source}"
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Analysing {task.description}..."),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(label)
        try:
            result = agent.analyze(source, output_path=output_path)
        except Exception as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    console.print()
    console.print(
        Panel(
            Markdown(result),
            title=f"[bold green]Analysis — {label}[/bold green]",
            border_style="green",
        )
    )

    if output_path:
        console.print(f"\n[dim]Summary saved to[/dim] [bold]{output_path}[/bold]")


@cli.command("compare")
@click.argument("sources", nargs=-1, required=True, metavar="<paper.pdf|arxiv_id>...")
@click.option(
    "-o",
    "--output",
    "output_path",
    default=None,
    metavar="FILE",
    help="Write the comparison to FILE.",
)
@click.option(
    "--api-key",
    envvar="ANTHROPIC_API_KEY",
    default=None,
    help="Anthropic API key (defaults to ANTHROPIC_API_KEY env var).",
)
def compare_cmd(
    sources: tuple[str, ...],
    output_path: str | None,
    api_key: str | None,
) -> None:
    """Compare two or more papers side by side.

    SOURCES is a space-separated list of PDF paths and/or arXiv IDs.

    \b
    Examples:
      paper-agent compare paper1.pdf paper2.pdf
      paper-agent compare 2301.07041 2305.12345 -o comparison.md
      paper-agent compare paper1.pdf 2305.12345
    """
    if len(sources) < 2:
        console.print("[bold red]Error:[/bold red] Please supply at least two papers to compare.")
        sys.exit(1)

    agent = _make_agent(api_key)

    labels = [
        Path(s).name if s.endswith(".pdf") else f"arXiv:{s}" for s in sources
    ]
    label_str = " vs ".join(labels)

    with Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]Comparing {task.description}..."),
        console=console,
        transient=True,
    ) as progress:
        progress.add_task(label_str)
        try:
            result = agent.compare(list(sources), output_path=output_path)
        except Exception as exc:
            console.print(f"[bold red]Error:[/bold red] {exc}")
            sys.exit(1)

    console.print()
    console.print(
        Panel(
            Markdown(result),
            title=f"[bold blue]Comparison — {label_str}[/bold blue]",
            border_style="blue",
        )
    )

    if output_path:
        console.print(f"\n[dim]Comparison saved to[/dim] [bold]{output_path}[/bold]")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
