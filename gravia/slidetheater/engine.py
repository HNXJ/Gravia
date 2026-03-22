"""SlideTheater engine: Markdown / DeepRead → Reveal.js HTML presentations.

Refactored from legacy slidetheater.py with:
- Jinja2 templating (dropped respysive dependency)
- Direct Reveal.js HTML generation
- Plotly figure embedding as standalone divs
- Madelane Golden Dark theme via configurable templates
- DeepRead analysis auto-splitting into slides
"""

import logging
import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import markdown as md_lib
from jinja2 import Environment, FileSystemLoader

from gravia.config import GraviaConfig
from gravia.utils import ensure_dir

logger = logging.getLogger("gravia.slidetheater")


@dataclass
class Slide:
    """A single presentation slide."""
    html: str = ""
    center: bool = False
    auto_animate: bool = False
    background: Optional[str] = None


class SlideTheaterEngine:
    """Interactive Reveal.js presentation generator.

    Usage:
        engine = SlideTheaterEngine(config)
        engine.add_title_slide("My Talk", subtitle="Subtitle")
        engine.add_markdown_slide(Path("content.md"))
        engine.add_plotly_slide("Data", fig)
        engine.export(Path("output/deck.html"))
    """

    def __init__(self, config: GraviaConfig):
        self.config = config
        self.sc = config.slidetheater
        self.template_dir = Path(__file__).parent / "templates"
        self.slides: list[Slide] = []
        self._has_plotly = False

        # Markdown processor with extensions
        self._md = md_lib.Markdown(
            extensions=["tables", "fenced_code", "attr_list", "toc"],
        )

    def _reset_md(self):
        """Reset the markdown processor between files."""
        self._md.reset()

    # -- Slide Builders --

    def add_title_slide(
        self,
        title: str,
        subtitle: str = "",
        author: str = "Hamed Nejat",
        affiliation: str = "PhD Candidate | Vanderbilt University",
        vu_logo: Optional[str] = None,
        blab_logo: Optional[str] = None,
    ):
        """Add a branded title slide."""
        parts = []

        # Logos
        if vu_logo or blab_logo:
            logo_html = '<div class="logo-container">'
            if vu_logo:
                logo_html += f'<img src="{vu_logo}" class="vu-logo" alt="VU">'
            if blab_logo:
                logo_html += f'<img src="{blab_logo}" class="blab-logo" alt="BastosLab">'
            logo_html += '</div>'
            parts.append(logo_html)

        parts.append(f"<h1>{title}</h1>")
        if subtitle:
            parts.append(f'<h3 class="cyan-text">{subtitle}</h3>')

        parts.append(
            f'<div style="margin-top: 40px; font-size: 0.6em; color: #CFB87C;">'
            f'<p><b>{author}</b></p>'
            f'<p>{affiliation}</p>'
            f'</div>'
        )

        self.slides.append(Slide(html="\n".join(parts), center=True))
        logger.info("✅ Added title slide: %s", title)

    def add_markdown_slide(
        self,
        md_source: Path | str,
        center: bool = False,
        auto_animate: bool = False,
    ):
        """Parse a Markdown file or string and add as a slide.

        Args:
            md_source: Path to .md file or raw Markdown string.
            center: Center the slide content.
            auto_animate: Enable Reveal.js auto-animate.
        """
        if isinstance(md_source, Path):
            if not md_source.exists():
                logger.warning("Markdown file not found: %s", md_source)
                return
            content = md_source.read_text(encoding="utf-8")
        else:
            content = md_source

        self._reset_md()

        # Split title from body (first # heading)
        lines = content.strip().split("\n")
        title = ""
        body_lines = lines

        if lines and lines[0].startswith("#"):
            title = lines[0].lstrip("# ").strip()
            body_lines = lines[1:]

        body_html = self._md.convert("\n".join(body_lines))

        parts = []
        if title:
            parts.append(f"<h2>{title}</h2>")
        parts.append(body_html)

        self.slides.append(Slide(
            html="\n".join(parts),
            center=center,
            auto_animate=auto_animate,
        ))
        logger.info("✅ Added markdown slide: %s", title or "(untitled)")

    def add_html_slide(
        self,
        html: str,
        center: bool = False,
        auto_animate: bool = False,
        background: Optional[str] = None,
    ):
        """Add a raw HTML slide."""
        self.slides.append(Slide(
            html=html,
            center=center,
            auto_animate=auto_animate,
            background=background,
        ))

    def add_plotly_slide(self, title: str, fig, description: str = ""):
        """Embed a Plotly figure as an interactive slide.

        Args:
            title: Slide title.
            fig: A plotly.graph_objects.Figure instance.
            description: Optional caption below the figure.
        """
        self._has_plotly = True
        div_id = f"plotly-{uuid.uuid4().hex[:8]}"

        # Generate standalone Plotly HTML div
        fig_html = fig.to_html(
            include_plotlyjs=False,
            full_html=False,
            div_id=div_id,
        )

        parts = [
            f"<h2>{title}</h2>",
            f'<div class="plotly-container">{fig_html}</div>',
        ]
        if description:
            parts.append(f'<p style="font-size: 0.6em; opacity: 0.8;">{description}</p>')

        self.slides.append(Slide(html="\n".join(parts)))
        logger.info("✅ Added Plotly slide: %s", title)

    def add_deepread_analysis(self, md_path: Path):
        """Split a DeepRead analysis file into multiple slides.

        Parses the structured Markdown output from DeepRead and creates
        one slide per ## section, with the paper title as a grand intro slide.

        Args:
            md_path: Path to a *_analysis.md file from DeepRead.
        """
        if not md_path.exists():
            logger.warning("Analysis file not found: %s", md_path)
            return

        content = md_path.read_text(encoding="utf-8")
        sections = re.split(r'## ', content)

        # Title slide from header
        title_section = sections[0]
        title_match = re.search(r'# (.*)', title_section)
        grand_title = title_match.group(1).strip() if title_match else md_path.stem
        doi_match = re.search(r'\*\*DOI\*\*: (.*)', title_section)
        doi = doi_match.group(1).strip() if doi_match else "N/A"

        self.slides.append(Slide(
            html=(
                f"<h1>{grand_title}</h1>\n"
                f'<h3>DOI: {doi}</h3>\n'
                f'<p class="fragment">DeepRead Automated Analysis</p>'
            ),
            center=True,
        ))

        # Content slides
        self._reset_md()
        for section in sections[1:]:
            lines = section.split("\n")
            s_title = lines[0].strip()
            s_body = self._md.convert("\n".join(lines[1:]))
            self._md.reset()

            self.slides.append(Slide(
                html=f"<h2>{s_title}</h2>\n{s_body}",
            ))

        logger.info("📚 Integrated %d slides from: %s", len(sections), grand_title[:50])

    # -- Export --

    def export(
        self,
        output_path: Path,
        theme: Optional[str] = None,
        footer_text: str = "Hamed Nejat | BastosLab | Vanderbilt University",
        deck_title: Optional[str] = None,
    ) -> Path:
        """Render all slides into a portable Reveal.js HTML file.

        Args:
            output_path: Destination HTML file path.
            theme: Template name (default: madelane).
            footer_text: Footer text shown on all slides.
            deck_title: HTML <title> for the deck.

        Returns:
            Path to the generated HTML file.
        """
        theme = theme or self.sc.default_theme
        output_path = Path(output_path).resolve()
        ensure_dir(output_path.parent)

        # Auto-detect deck title
        if not deck_title and self.slides:
            # Try extracting from first h1
            first = self.slides[0].html
            h1_match = re.search(r'<h1>(.*?)</h1>', first)
            deck_title = h1_match.group(1) if h1_match else "Gravia Presentation"

        # Render via Jinja2
        env = Environment(loader=FileSystemLoader(str(self.template_dir)))
        template = env.get_template(f"{theme}.html.j2")

        html = template.render(
            slides=self.slides,
            deck_title=deck_title,
            footer_text=footer_text,
            reveal_version=self.sc.reveal_version,
            transition=self.sc.transition,
            plotly_js=self._has_plotly,
        )

        output_path.write_text(html, encoding="utf-8")
        logger.info("🚀 Presentation exported: %s (%d slides)", output_path, len(self.slides))
        return output_path

    def clear(self):
        """Reset the slide deck."""
        self.slides.clear()
        self._has_plotly = False
