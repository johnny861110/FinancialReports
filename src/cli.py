"""
Financial Reports Insight Engine CLI.
Entry point: `fr` command.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress
from rich.table import Table

from src.domain.identity import FilingIdentity
from src.pipeline.run import STAGES

app = typer.Typer(
    name="fr",
    help="Financial Reports Insight Engine - 財報分析引擎",
    invoke_without_command=True,
)
console = Console()


@app.callback()
def main(ctx: typer.Context) -> None:
    if ctx.invoked_subcommand is None:
        typer.echo(ctx.get_help())
        raise typer.Exit()


def _make_store(db: str | None):
    from src.storage.store import FilingStore

    return FilingStore(db)


def _make_identity(stock: str, year: int, quarter: str) -> FilingIdentity:
    return FilingIdentity(stock_code=stock, year=year, quarter=quarter)


# ── ingest ────────────────────────────────────────────────────────────────────


@app.command()
def ingest(
    stock: str = typer.Argument(..., help="Stock code, e.g. 2330"),
    year: int = typer.Argument(..., help="CE year, e.g. 2024"),
    quarter: str = typer.Argument(..., help="Quarter: Q1|Q2|Q3|Q4"),
    db: str | None = typer.Option(None, help="Database URL (defaults to $FR_DATABASE_URL)"),
    output_dir: str = typer.Option("data/raw", help="Directory for downloaded files"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-ingest even if already done"),
) -> None:
    """Download XBRL/PDF source documents."""
    identity = _make_identity(stock, year, quarter)
    store = _make_store(db)
    from src.pipeline.ingest import run_ingest

    console.print(f"[bold cyan]Ingesting {identity.filing_key}...[/bold cyan]")
    result = run_ingest(identity, store, Path(output_dir), force=force)
    _print_result("Ingest", result)


# ── extract ───────────────────────────────────────────────────────────────────


@app.command()
def extract(
    stock: str = typer.Argument(..., help="Stock code"),
    year: int = typer.Argument(..., help="CE year"),
    quarter: str = typer.Argument(..., help="Quarter: Q1|Q2|Q3|Q4"),
    db: str | None = typer.Option(None, help="Database URL (defaults to $FR_DATABASE_URL)"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-extract even if already done"),
) -> None:
    """Parse source documents and extract financial facts."""
    identity = _make_identity(stock, year, quarter)
    store = _make_store(db)
    from src.pipeline.run import _recover_doc_paths

    doc_paths = _recover_doc_paths(identity, store)
    from src.pipeline.extract import run_extract

    console.print(f"[bold cyan]Extracting {identity.filing_key}...[/bold cyan]")
    result = run_extract(identity, store, doc_paths, force=force)
    _print_result("Extract", result)


# ── validate ──────────────────────────────────────────────────────────────────


@app.command()
def validate(
    stock: str = typer.Argument(..., help="Stock code"),
    year: int = typer.Argument(..., help="CE year"),
    quarter: str = typer.Argument(..., help="Quarter: Q1|Q2|Q3|Q4"),
    db: str | None = typer.Option(None, help="Database URL (defaults to $FR_DATABASE_URL)"),
) -> None:
    """Validate financial data quality and run consistency checks."""
    identity = _make_identity(stock, year, quarter)
    store = _make_store(db)
    from src.pipeline.validate import run_validate

    console.print(f"[bold cyan]Validating {identity.filing_key}...[/bold cyan]")
    result = run_validate(identity, store)
    _print_result("Validate", result)
    if result.get("score") is not None:
        console.print(f"\n[bold]Quality Score:[/bold] {result['score']:.2%}")


# ── insights ──────────────────────────────────────────────────────────────────


@app.command()
def insights(
    stock: str = typer.Argument(..., help="Stock code"),
    year: int = typer.Argument(..., help="CE year"),
    quarter: str = typer.Argument(..., help="Quarter: Q1|Q2|Q3|Q4"),
    db: str | None = typer.Option(None, help="Database URL (defaults to $FR_DATABASE_URL)"),
) -> None:
    """Compute financial metrics and build insight cards."""
    identity = _make_identity(stock, year, quarter)
    store = _make_store(db)
    from src.pipeline.build_insights import run_build_insights

    console.print(f"[bold cyan]Building insights for {identity.filing_key}...[/bold cyan]")
    result = run_build_insights(identity, store)
    _print_result("Insights", result)


# ── run ───────────────────────────────────────────────────────────────────────


@app.command()
def run(
    stock: str = typer.Argument(..., help="Stock code"),
    year: int = typer.Argument(..., help="CE year"),
    quarter: str = typer.Argument(..., help="Quarter: Q1|Q2|Q3|Q4"),
    db: str | None = typer.Option(None, help="Database URL (defaults to $FR_DATABASE_URL)"),
    output_dir: str = typer.Option("data/raw", help="Directory for downloaded files"),
    stages: str | None = typer.Option(
        None, help=f"Comma-separated stages to run. Default: all. Options: {','.join(STAGES)}"
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Force re-run all stages"),
) -> None:
    """Run the full pipeline (ingest → extract → validate → insights)."""
    identity = _make_identity(stock, year, quarter)
    store = _make_store(db)
    stage_list = [s.strip() for s in stages.split(",")] if stages else None

    from src.pipeline.run import run_pipeline

    console.print(Panel(f"[bold cyan]Running pipeline for {identity.filing_key}[/bold cyan]"))
    results = run_pipeline(identity, store, Path(output_dir), stages=stage_list, force=force)

    for stage_name, result in results.items():
        status = result.get("status", "unknown")
        color = {"completed": "green", "skipped": "yellow", "failed": "red"}.get(status, "white")
        console.print(f"  [{color}]{stage_name}: {status}[/{color}]")
        if status == "failed" and result.get("error"):
            console.print(f"    Error: {result['error']}", style="red")


# ── ask ───────────────────────────────────────────────────────────────────────


@app.command()
def ask(
    question: str = typer.Argument(..., help="Your question about the filing"),
    stock: str = typer.Option(..., "--stock", "-s", help="Stock code"),
    year: int = typer.Option(..., "--year", "-y", help="CE year"),
    quarter: str = typer.Option(..., "--quarter", "-q", help="Quarter: Q1|Q2|Q3|Q4"),
    db: str | None = typer.Option(None, help="Database URL (defaults to $FR_DATABASE_URL)"),
) -> None:
    """Query financial insights with natural language."""
    identity = _make_identity(stock, year, quarter)
    store = _make_store(db)

    from src.agent.context_builder import build_context_pack
    from src.agent.query_service import FinancialQueryService

    service = FinancialQueryService(store)
    console.print(f"\n[bold cyan]Building context for {identity.filing_key}...[/bold cyan]")
    ctx = build_context_pack(service, stock, year, quarter, question=question)

    # Try LLM if available
    _try_llm_answer(question, ctx)

    # Always show context pack in rich format
    _display_context_pack(ctx)


def _try_llm_answer(question: str, ctx: dict) -> None:
    """Attempt to answer via OpenAI; silently skip if not available."""
    try:
        import os

        import openai

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return

        client = openai.OpenAI(api_key=api_key)
        context_text = json.dumps(
            {
                "key_facts": ctx.get("facts_dict", {}),
                "metrics": ctx.get("metrics", {}),
                "comparisons_yoy": ctx.get("comparisons", {}).get("yoy", [])[:10],
                "events": ctx.get("events", []),
                "insight_cards": [
                    {"title": c["title"], "summary": c["summary"]}
                    for c in ctx.get("insight_cards", [])
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        system_prompt = (
            "You are a professional Taiwan equity analyst. "
            "Answer questions about financial reports based on the provided data. "
            "Be concise, precise, and cite specific numbers."
        )
        user_prompt = f"Financial data:\n{context_text}\n\nQuestion: {question}"
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=800,
        )
        answer = response.choices[0].message.content
        console.print(Panel(answer, title="[bold green]AI Answer[/bold green]", expand=False))
    except ImportError:
        pass
    except Exception as exc:
        console.print(f"[yellow]LLM unavailable: {exc}[/yellow]")


def _display_context_pack(ctx: dict) -> None:
    """Display context pack as rich tables."""
    # Filing metadata
    filing = ctx.get("filing", {})
    console.print(
        Panel(
            f"[bold]{filing.get('filing_key')}[/bold]  "
            f"Status: {filing.get('status', 'unknown')}  "
            f"Quality: {ctx.get('quality_score', 0):.1%}",
            title="Filing",
        )
    )

    # Key facts
    facts_dict = ctx.get("facts_dict", {})
    if facts_dict:
        t = Table("Field", "Value (TWD thousands)", title="Key Financial Facts")
        key_fields = [
            "net_revenue",
            "gross_profit",
            "operating_income",
            "net_income",
            "eps_basic",
            "total_assets",
            "equity",
            "operating_cash_flow",
        ]
        for field in key_fields:
            val = facts_dict.get(field)
            if val is not None:
                t.add_row(field, f"{val:,.0f}" if abs(val) > 10 else f"{val:.2f}")
        console.print(t)

    # Metrics
    metrics = ctx.get("metrics", {})
    if metrics:
        t = Table("Metric", "Value", title="Computed Metrics")
        for k, v in sorted(metrics.items()):
            t.add_row(k, f"{v:.4f}")
        console.print(t)

    # YoY comparisons
    yoy = ctx.get("comparisons", {}).get("yoy", [])
    if yoy:
        t = Table("Field", "Current", "Prior", "Change%", "Direction", title="YoY Comparisons")
        for c in yoy[:10]:
            pct = f"{c['change_pct']:.1f}%" if c.get("change_pct") is not None else "N/A"
            t.add_row(
                c["field"],
                f"{c['current_value']:,.0f}",
                f"{c['prior_value']:,.0f}",
                pct,
                c.get("direction", ""),
            )
        console.print(t)

    # Insight cards
    cards = ctx.get("insight_cards", [])
    if cards:
        for card in cards:
            sentiment_color = {"positive": "green", "negative": "red", "neutral": "white"}.get(
                card.get("sentiment", "neutral"), "white"
            )
            console.print(
                Panel(
                    f"[{sentiment_color}]{card['summary']}[/{sentiment_color}]",
                    title=f"[bold]{card['title']}[/bold] ({card['card_type']})",
                    expand=False,
                )
            )

    # Evidence chunks
    chunks = ctx.get("evidence_chunks", [])[:3]
    if chunks:
        console.print("\n[bold]Relevant Text Evidence:[/bold]")
        for chunk in chunks:
            console.print(
                Panel(
                    chunk["content"][:400] + ("..." if len(chunk["content"]) > 400 else ""),
                    title=f"Page {chunk.get('page_number')} | {chunk.get('section_type', '')}",
                    expand=False,
                )
            )


# ── batch ─────────────────────────────────────────────────────────────────────


@app.command()
def batch(
    config_file: str = typer.Argument(..., help="JSON config file with list of filings"),
    db: str | None = typer.Option(None, help="Database URL (defaults to $FR_DATABASE_URL)"),
    output_dir: str = typer.Option("data/raw", help="Output directory for downloads"),
    stages: str | None = typer.Option(None, help="Comma-separated stages to run"),
    concurrency: int = typer.Option(4, "--concurrency", "-c", help="Max parallel filings"),
) -> None:
    """Run pipeline on multiple filings concurrently from a JSON config file."""
    import asyncio

    config_path = Path(config_file)
    if not config_path.exists():
        console.print(f"[red]Config file not found: {config_file}[/red]")
        raise typer.Exit(1)

    with open(config_path, encoding="utf-8") as f:
        filings_config = json.load(f)

    store = _make_store(db)
    stage_list = [s.strip() for s in stages.split(",")] if stages else None

    filings = [
        FilingIdentity(
            stock_code=item.get("stock_code") or item.get("stock"),
            year=int(item["year"]),
            quarter=item.get("quarter", "Q1"),
        )
        for item in filings_config
    ]

    console.print(
        f"[bold cyan]Batch: {len(filings)} filings, concurrency={concurrency}[/bold cyan]"
    )

    from src.pipeline.run import run_batch_async

    batch_results = asyncio.run(
        run_batch_async(
            filings, store, Path(output_dir), stages=stage_list, concurrency=concurrency
        )
    )

    # Print summary table
    t = Table("Filing", "ingest", "extract", "validate", "insights", title="Batch Results")
    ok = fail = 0
    for res in batch_results:
        fk = res.get("filing_key", "?")
        if "error" in res:
            t.add_row(fk, "[red]ERR[/red]", "", "", "")
            fail += 1
        else:
            stages_res = res.get("results", {})

            def _cell(s: str) -> str:
                st = stages_res.get(s, {}).get("status", "-")
                color = {"completed": "green", "skipped": "yellow", "failed": "red"}.get(
                    st, "white"
                )
                return f"[{color}]{st}[/{color}]"

            t.add_row(fk, _cell("ingest"), _cell("extract"), _cell("validate"), _cell("insights"))
            if any(v.get("status") == "failed" for v in stages_res.values()):
                fail += 1
            else:
                ok += 1

    console.print(t)
    console.print(f"\n[green]{ok} succeeded[/green]  [red]{fail} failed[/red]")


# ── show ──────────────────────────────────────────────────────────────────────


@app.command()
def show(
    stock: str = typer.Argument(..., help="Stock code"),
    year: int = typer.Argument(..., help="CE year"),
    quarter: str = typer.Argument(..., help="Quarter: Q1|Q2|Q3|Q4"),
    db: str | None = typer.Option(None, help="Database URL (defaults to $FR_DATABASE_URL)"),
    format: str = typer.Option("table", help="Output format: table|json|summary"),
) -> None:
    """Show filing data: facts, metrics, and insight cards."""
    identity = _make_identity(stock, year, quarter)
    store = _make_store(db)
    fk = identity.filing_key

    if format == "json":
        from src.storage.json_exporter import export_filing

        data = export_filing(store, fk)
        console.print_json(json.dumps(data, ensure_ascii=False, indent=2))
        return

    # Summary
    status = store.get_filing_status(fk)
    if status is None:
        console.print(
            f"[yellow]No data found for {fk}. Run `fr run {stock} {year} {quarter}` first.[/yellow]"
        )
        return

    console.print(Panel(f"[bold]{fk}[/bold]  Status: {status}", title="Filing"))

    facts_dict = store.get_facts_dict(fk)
    if facts_dict:
        t = Table("Field", "Value", title="Financial Facts")
        for field, value in sorted(facts_dict.items()):
            fmt = f"{value:,.0f}" if abs(value) > 10 else f"{value:.4f}"
            t.add_row(field, fmt)
        console.print(t)

    metrics = store.get_metrics(fk)
    if metrics:
        t = Table("Metric", "Value", "Formula", title="Computed Metrics")
        for m in metrics:
            t.add_row(m["metric_name"], f"{m['value']:.4f}", m.get("formula") or "")
        console.print(t)

    cards = store.get_insight_cards(fk)
    if cards:
        t = Table("Type", "Title", "Summary", "Sentiment", title="Insight Cards")
        for c in cards:
            t.add_row(c["card_type"], c["title"], c["summary"][:60], c.get("sentiment") or "")
        console.print(t)


# ── helpers ───────────────────────────────────────────────────────────────────


def _print_result(stage: str, result: dict) -> None:
    status = result.get("status", "unknown")
    color = {"completed": "green", "skipped": "yellow", "failed": "red"}.get(status, "white")
    console.print(f"[{color}]{stage} {status}[/{color}]")
    for k, v in result.items():
        if k != "status":
            console.print(f"  {k}: {v}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    app()


@app.command()
def embed(
    stock: str | None = typer.Option(None, help="Only embed this stock code"),
    db: str | None = typer.Option(None, help="Database URL (defaults to $FR_DATABASE_URL)"),
    batch_size: int = typer.Option(64, help="Chunks encoded per forward pass"),
    limit: int | None = typer.Option(None, help="Stop after this many chunks (for trials)"),
) -> None:
    """Generate chunk embeddings for question-directed retrieval.

    Requires the vector extra: `uv sync --extra vector`. Already-embedded
    chunks are skipped, so the command is resumable.
    """
    from sqlalchemy import text

    from src.agent.embedding import EMBEDDING_DIM, encode, is_available, model_name

    if not is_available():
        console.print("[red]sentence-transformers is not installed.[/red]")
        console.print("Install it with: [cyan]uv sync --extra vector[/cyan]")
        raise typer.Exit(1)

    store = _make_store(db)
    name = model_name()

    where = "WHERE ce.chunk_id IS NULL"
    params: dict = {}
    if stock:
        where += " AND f.filing_key LIKE :prefix"
        params["prefix"] = f"{stock}_%"

    with store.conn() as conn:
        pending = conn.execute(
            text(
                "SELECT COUNT(*) FROM document_chunks dc"
                " JOIN source_documents sd ON sd.id=dc.doc_id"
                " JOIN filings f ON f.id=sd.filing_id"
                " LEFT JOIN chunk_embeddings ce ON ce.chunk_id=dc.id " + where
            ),
            params,
        ).scalar_one()

    if limit is not None:
        pending = min(pending, limit)
    if not pending:
        console.print("[green]Nothing to embed — every chunk already has an embedding.[/green]")
        return

    console.print(
        f"Embedding [cyan]{pending:,}[/cyan] chunks with [cyan]{name}[/cyan] ({EMBEDDING_DIM}d)"
    )

    done = 0
    with Progress() as progress:
        task = progress.add_task("encoding", total=pending)
        while done < pending:
            take = min(batch_size, pending - done)
            with store.conn() as conn:
                rows = conn.execute(
                    text(
                        "SELECT dc.id, dc.content FROM document_chunks dc"
                        " JOIN source_documents sd ON sd.id=dc.doc_id"
                        " JOIN filings f ON f.id=sd.filing_id"
                        " LEFT JOIN chunk_embeddings ce ON ce.chunk_id=dc.id "
                        + where
                        + " ORDER BY dc.id LIMIT :take"
                    ),
                    {**params, "take": take},
                ).fetchall()
            if not rows:
                break

            vectors = encode([row[1] for row in rows], batch_size=batch_size)
            payload = [
                {"cid": row[0], "model": name, "vec": str(vector)}
                for row, vector in zip(rows, vectors)
            ]
            with store.conn() as conn:
                conn.execute(
                    text(
                        "INSERT INTO chunk_embeddings(chunk_id, model_name, embedding)"
                        " VALUES(:cid, :model, CAST(:vec AS vector))"
                        " ON CONFLICT (chunk_id) DO UPDATE SET"
                        " embedding=EXCLUDED.embedding, model_name=EXCLUDED.model_name"
                    ),
                    payload,
                )
            done += len(rows)
            progress.update(task, advance=len(rows))

    console.print(f"[green]Embedded {done:,} chunks.[/green]")
