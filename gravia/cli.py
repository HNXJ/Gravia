"""Gravia CLI: Professional research factory entry point.

Subcommands:
    gravia read   — Analyze papers with DeepRead (VLM)
    gravia write  — Compose manuscripts (LaTeX/DOCX)
    gravia slide  — Generate interactive presentations
    gravia geval  — Scientific Fact-Check (Teacher-Student)
    gravia bridge — Secure P2P relay messaging
"""

import asyncio
import sys
import json
from pathlib import Path

import click

from gravia import __version__
from gravia.config import GraviaConfig
from gravia.utils import setup_logging


@click.group()
@click.version_option(__version__, prog_name="gravia")
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging.")
@click.option("--config", "-c", type=click.Path(exists=True), default=None, help="Path to .gravia.toml config.")
@click.pass_context
def main(ctx, verbose, config):
    """Gravia: Professional Research Factory.

    A unified engine for paper analysis, manuscript synthesis, 
    interactive presentations, and formal scientific validation.
    """
    cfg = GraviaConfig.load(Path(config) if config else None)
    cfg.verbose = verbose or cfg.verbose
    ctx.ensure_object(dict)
    ctx.obj["config"] = cfg
    setup_logging(cfg.verbose)


# ── DeepRead (Read) ──────────────────────────────────────

@main.command()
@click.argument("pdf_path", required=False, type=click.Path())
@click.option("--batch", is_flag=True, help="Process all PDFs in input_dir.")
@click.option("--input-dir", type=click.Path(exists=True), help="Override input directory.")
@click.option("--output-dir", type=click.Path(), help="Override output directory.")
@click.option("--max-concurrent", default=3, help="Max parallel VLM requests.")
@click.pass_context
def read(ctx, pdf_path, batch, input_dir, output_dir, max_concurrent):
    """Analyze scientific papers with DeepRead VLM engine."""
    from gravia.deepread import DeepReadEngine

    cfg = ctx.obj["config"]
    engine = DeepReadEngine(cfg)

    if batch or not pdf_path:
        in_dir = Path(input_dir) if input_dir else None
        out_dir = Path(output_dir) if output_dir else None
        results = asyncio.run(engine.process_batch(in_dir, out_dir, max_concurrent))
        sys.exit(0 if all(r.success for r in results) else 1)
    else:
        result = asyncio.run(engine.process_paper(Path(pdf_path)))
        if result.success:
            out_dir = Path(output_dir) if output_dir else cfg.output_dir
            out_dir.mkdir(parents=True, exist_ok=True)
            out_path = out_dir / f"{Path(pdf_path).stem}_analysis.md"
            out_path.write_text(result.markdown, encoding="utf-8")
            click.echo(f"✅ Saved: {out_path}")
        else:
            click.echo(f"❌ Failed: {result.error}", err=True)
            sys.exit(1)


# ── Writer (Write) ───────────────────────────────────────

@main.command()
@click.argument("markdown", type=click.Path(exists=True))
@click.option("--title", help="Paper title.")
@click.option("--authors", help="Author list.")
@click.option("--affil", help="Affiliations.")
@click.option("--abstract", help="Abstract text or path to abstract file.")
@click.option("--bib", help="Path to bibliography .bib file.")
@click.option("--template", default="biorxiv", help="LaTeX template name.")
@click.option("--skill", help="Use a specific writing skill (e.g., neuro-mimicry).")
@click.option("--pdf", is_flag=True, help="Compile to PDF via pdflatex.")
@click.pass_context
def write(ctx, markdown, title, authors, affil, abstract, bib, template, skill, pdf):
    """Compose manuscripts into LaTeX/DOCX from Markdown."""
    from gravia.writer import WriterEngine

    cfg = ctx.obj["config"]
    engine = WriterEngine(cfg)

    # Handle abstract from file
    abstract_content = None
    if abstract:
        abs_path = Path(abstract)
        if abs_path.exists():
            abstract_content = abs_path.read_text(encoding="utf-8")
        else:
            abstract_content = abstract

    # Note: Skill support is a placeholder for future LLM-rewriting step
    if skill:
        click.echo(f"🧬 Applying Writing Skill: {skill}...")

    outputs = engine.compose(
        Path(markdown),
        title=title,
        authors=authors,
        affiliations=affil,
        abstract=abstract_content,
        bib_file=bib,
        template=template,
        compile_pdf=pdf,
    )

    success = any(v is not None for v in outputs.values())
    sys.exit(0 if success else 1)


# ── SlideTheater (Slide) ──────────────────────────────────

@main.command()
@click.option("--project", type=click.Path(exists=True), help="Project root with content/ dir.")
@click.option("--analysis-dir", type=click.Path(exists=True), help="DeepRead markdowns directory.")
@click.option("--output", "-o", type=click.Path(), default="presentation.html", help="Output HTML path.")
@click.option("--theme", default="madelane", help="Reveal.js theme template.")
@click.option("--title", default="Gravia Presentation", help="Deck title.")
@click.pass_context
def slide(ctx, project, analysis_dir, output, theme, title):
    """Generate interactive Reveal.js presentations."""
    from gravia.slidetheater import SlideTheaterEngine
    import os

    cfg = ctx.obj["config"]
    engine = SlideTheaterEngine(cfg)

    # Title slide
    engine.add_title_slide(title)

    # Add project content if available
    if project:
        content_dir = Path(project) / "content"
        if content_dir.exists():
            for md in sorted(content_dir.glob("*.md")):
                engine.add_markdown_slide(md)

    # Integrate DeepRead analyses
    if analysis_dir:
        analysis_path = Path(analysis_dir)
        analysis_files = sorted(
            analysis_path.glob("*_analysis.md"),
            key=os.path.getmtime,
            reverse=True,
        )[:5]

        for af in analysis_files:
            engine.add_deepread_analysis(af)

    # Export
    out_path = engine.export(Path(output), theme=theme, deck_title=title)
    click.echo(f"🚀 Exported: {out_path}")


# ── G-Eval (Geval) ───────────────────────────────────────

@main.command()
@click.argument("input_data", type=click.Path(exists=True))
@click.option("--teacher", default="/Users/hamednejat/workspace/Warehouse/mlx_models/Qwen3.5-27B-Opus-Reasoning-6bit", help="Path to Teacher-Judge model.")
@click.option("--rubric", type=click.Path(exists=True), help="Path to custom evaluation rubric.")
@click.option("--output", "-o", type=click.Path(), help="Path to save results (JSONL).")
@click.pass_context
def geval(ctx, input_data, teacher, rubric, output):
    """Perform scientific fact-check (LLM-as-a-judge)."""
    from gravia.geval.engine import GevalEngine
    import re

    rubric_content = None
    if rubric:
        rubric_content = Path(rubric).read_text(encoding="utf-8")

    engine = GevalEngine(teacher)
    results = engine.fact_check(input_data, rubric=rubric_content)

    for res in results:
        fc = res.get("fact_check", {})
        score = fc.get("score", "N/A")
        reasoning = fc.get("reasoning", "No reasoning provided.")
        click.echo(f"📊 Score: {score}/5")
        click.echo(f"💡 Reasoning: {reasoning}\n")

    if output:
        out_path = Path(output)
        with open(out_path, "w") as f:
            for r in results:
                f.write(json.dumps(r) + "\n")
        click.echo(f"💾 Saved results to: {out_path}")


# ── Bridger (Bridge) ─────────────────────────────────────

@main.command()
@click.option("--relay", help="Git relay URL.")
@click.option("--partner", type=click.Path(exists=True), help="Path to partner public key.")
@click.option("--send", help="Send a message (text or path to file).")
@click.option("--mode", default="text", help="Message mode (text, file, url, markdown).")
@click.option("--check", is_flag=True, help="Check for new messages.")
@click.option("--read", is_flag=True, help="Read and decrypt the next message.")
@click.option("--address", is_flag=True, help="Show my Bridger address.")
@click.option("--partner-id", help="Partner ID hash for targeted send.")
@click.pass_context
def bridge(ctx, relay, partner, send, mode, check, read, address, partner_id):
    """Secure P2P relay messaging via Git."""
    from gravia.bridger.bridger import BridgerMod

    # Default relay from config if available
    cfg = ctx.obj["config"]
    relay_url = relay or getattr(cfg, "bridger_relay", "")

    bridger = BridgerMod(relay_url=relay_url, partner_pubkey_path=partner)

    if address:
        click.echo(f"📫 MY ADDRESS: {bridger.get_my_address()}")
        click.echo(f"🆔 MY ID HASH: {bridger.my_id_hash}")
    
    elif send:
        bridger.send(mode, send, partner_id_hash=partner_id)
    
    elif check:
        bridger.check()
    
    elif read:
        msg = bridger.read()
        if msg:
            click.echo(f"📬 FROM: {msg['sender']} ({msg['mode']})")
            click.echo(f"📝 DATA: {msg['data']}")
        else:
            click.echo("📭 No messages.")


if __name__ == "__main__":
    main()
