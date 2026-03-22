"""Writer engine: Markdown → LaTeX / DOCX manuscript synthesis.

Refactored from legacy writer_core.py with:
- Jinja2 templating (no more raw str.replace)
- Class-based engine with config injection
- Separated concerns: frontmatter parsing, LaTeX render, DOCX render, PDF compile
- Better pdflatex error reporting
- Multiple template support via --template flag
"""

import logging
import re
import shutil
from pathlib import Path
from typing import Optional

import pypandoc
import yaml
from jinja2 import Environment, FileSystemLoader

from gravia.config import GraviaConfig
from gravia.utils import ensure_dir, run_subprocess

logger = logging.getLogger("gravia.writer")

# Jinja2 uses {{ }} by default, which clashes with LaTeX.
# We use ((( ))) for variables and (% %) for blocks.
_JINJA_LATEX_ENV_KWARGS = dict(
    block_start_string="(%",
    block_end_string="%)",
    variable_start_string="(((",
    variable_end_string=")))",
    comment_start_string="(#",
    comment_end_string="#)",
    autoescape=False,
)


class WriterEngine:
    """Manuscript synthesis engine: Markdown → LaTeX / DOCX.

    Usage:
        engine = WriterEngine(config)
        engine.compose(
            Path("draft.md"),
            title="My Paper",
            compile_pdf=True,
        )
    """

    def __init__(self, config: GraviaConfig):
        self.config = config
        self.wc = config.writer
        self.template_dir = Path(__file__).parent / "templates"

    # -- Frontmatter Parsing --

    @staticmethod
    def parse_frontmatter(md_path: Path) -> tuple[dict, str]:
        """Parse YAML frontmatter from a Markdown file.

        Args:
            md_path: Path to the Markdown file.

        Returns:
            (metadata_dict, raw_content_string) tuple.
        """
        content = md_path.read_text(encoding="utf-8")
        metadata: dict = {}

        match = re.search(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
        if match:
            try:
                metadata = yaml.safe_load(match.group(1)) or {}
            except yaml.YAMLError as e:
                logger.warning("Failed to parse YAML frontmatter: %s", e)

        return metadata, content

    @staticmethod
    def strip_frontmatter(content: str) -> str:
        """Remove YAML frontmatter from Markdown content."""
        return re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

    # -- LaTeX Rendering --

    def render_latex(
        self,
        md_body: str,
        *,
        title: str,
        authors: str,
        affiliations: str,
        abstract: str = "",
        bib_name: Optional[str] = None,
        corresponding_email: Optional[str] = None,
        template: str = "biorxiv",
    ) -> str:
        """Render Markdown body into a complete LaTeX document via Jinja2 template.

        Args:
            md_body: Markdown content (frontmatter stripped).
            title: Paper title.
            authors: Author list string.
            affiliations: Affiliation string.
            abstract: Abstract text.
            bib_name: Bibliography file basename (without .bib).
            corresponding_email: Optional email to override default.
            template: Template name (maps to templates/{name}.tex.j2).

        Returns:
            Complete LaTeX document string.
        """
        # Convert MD to LaTeX fragment via pypandoc
        body_tex = pypandoc.convert_text(md_body, "latex", format="md")

        # Load and render Jinja2 template
        env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            **_JINJA_LATEX_ENV_KWARGS,
        )

        template_obj = env.get_template(f"{template}.tex.j2")
        return template_obj.render(
            title=title,
            authors=authors,
            affiliations=affiliations,
            abstract=abstract,
            body=body_tex,
            bib_name=bib_name,
            corresponding_email=corresponding_email,
        )

    # -- DOCX Rendering --

    @staticmethod
    def render_docx(md_path: Path, output_path: Path) -> Optional[Path]:
        """Convert Markdown to DOCX via pypandoc.

        Args:
            md_path: Input Markdown path.
            output_path: Output .docx path.

        Returns:
            Path to generated DOCX, or None on failure.
        """
        logger.info("Generating DOCX...")
        try:
            pypandoc.convert_file(str(md_path), "docx", outputfile=str(output_path))
            logger.info("✅ DOCX: %s", output_path.name)
            return output_path
        except Exception as e:
            logger.error("❌ DOCX generation failed: %s", e)
            return None

    # -- PDF Compilation --

    @staticmethod
    def compile_pdf(tex_path: Path) -> Optional[Path]:
        """Compile LaTeX to PDF via pdflatex + bibtex.

        Runs the standard pdflatex → bibtex → pdflatex × 2 cycle.

        Args:
            tex_path: Path to .tex file.

        Returns:
            Path to generated PDF, or None on failure.
        """
        logger.info("Compiling PDF from %s ...", tex_path.name)
        output_dir = str(tex_path.parent)
        cmd_base = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-output-directory", output_dir,
            str(tex_path),
        ]

        try:
            # First pass
            run_subprocess(cmd_base)

            # BibTeX if aux exists
            aux_path = tex_path.with_suffix(".aux")
            if aux_path.exists():
                run_subprocess(["bibtex", str(aux_path)])
                run_subprocess(cmd_base)
                run_subprocess(cmd_base)

            pdf_path = tex_path.with_suffix(".pdf")
            if pdf_path.exists():
                logger.info("✅ PDF: %s", pdf_path.name)
                return pdf_path

            # Try to find useful error
            log_path = tex_path.with_suffix(".log")
            if log_path.exists():
                log_text = log_path.read_text(errors="ignore")
                errors = [ln for ln in log_text.split("\n") if ln.startswith("!")]
                if errors:
                    logger.error("LaTeX errors:\n%s", "\n".join(errors[:10]))

            logger.warning("PDF not found after compilation. Check logs.")
            return None

        except Exception as e:
            logger.error("❌ PDF compilation failed: %s", e)
            return None

    # -- Main Compose Pipeline --

    def compose(
        self,
        md_path: Path,
        *,
        title: Optional[str] = None,
        authors: Optional[str] = None,
        affiliations: Optional[str] = None,
        abstract: Optional[str] = None,
        bib_file: Optional[str] = None,
        template: Optional[str] = None,
        compile_pdf: bool = False,
    ) -> dict[str, Optional[Path]]:
        """Full composition pipeline: Markdown → LaTeX + DOCX (+ optional PDF).

        Args:
            md_path: Source Markdown file.
            title: Override title (falls back to frontmatter, then default).
            authors: Override authors.
            affiliations: Override affiliations.
            abstract: Abstract text or path to abstract file.
            bib_file: Path to .bib file.
            template: LaTeX template name.
            compile_pdf: Whether to compile LaTeX to PDF.

        Returns:
            Dict with keys 'tex', 'docx', 'pdf' mapping to output Paths or None.
        """
        md_path = Path(md_path).resolve()
        project_name = md_path.stem
        reports_dir = ensure_dir(md_path.parent / "reports")
        template = template or self.wc.default_template

        # Parse metadata
        metadata, raw_content = self.parse_frontmatter(md_path)

        title = title or metadata.get("title", "Untitled Paper")
        authors = authors or metadata.get("authors", "Author et al.")
        affiliations = affiliations or metadata.get("affiliations", "")
        abstract = abstract or metadata.get("abstract", "")
        bib_file = bib_file or metadata.get("bibliography")

        # Handle abstract from file
        if abstract and len(abstract) < 255 and Path(abstract).exists():
            abstract = Path(abstract).read_text(encoding="utf-8")

        logger.info("Composing: %s → %s", project_name, reports_dir)

        outputs: dict[str, Optional[Path]] = {"tex": None, "docx": None, "pdf": None}

        # Handle bibliography
        bib_name: Optional[str] = None
        if bib_file and bib_file not in ("None", ""):
            src_bib = Path(bib_file)
            if not src_bib.is_absolute():
                src_bib = Path.cwd() / bib_file
            if not src_bib.exists():
                # Fallback to legacy default
                legacy_bib = Path(__file__).parent.parent.parent / "writer" / "library.bib"
                if legacy_bib.exists():
                    src_bib = legacy_bib
                    logger.warning("Bib not found at %s, falling back to %s", bib_file, legacy_bib)
                else:
                    src_bib = None
                    logger.warning("No bibliography file found")

            if src_bib and src_bib.exists():
                dest_bib = reports_dir / f"{project_name}.bib"
                shutil.copy(src_bib, dest_bib)
                bib_name = project_name
                logger.info("Using bibliography: %s", src_bib.name)

        # 1. DOCX
        output_docx = reports_dir / f"{project_name}.docx"
        outputs["docx"] = self.render_docx(md_path, output_docx)

        # 2. LaTeX
        try:
            md_body = self.strip_frontmatter(raw_content)
            full_tex = self.render_latex(
                md_body,
                title=title,
                authors=authors,
                affiliations=affiliations,
                abstract=abstract,
                bib_name=bib_name,
                template=template,
            )
            output_tex = reports_dir / f"{project_name}.tex"
            output_tex.write_text(full_tex, encoding="utf-8")
            outputs["tex"] = output_tex
            logger.info("✅ LaTeX: %s", output_tex.name)

            # 3. Optional PDF
            if compile_pdf or self.wc.compile_pdf:
                outputs["pdf"] = self.compile_pdf(output_tex)

        except Exception as e:
            logger.error("❌ LaTeX generation failed: %s", e)

        # Summary
        logger.info("── Compose complete ──")
        for fmt, path in outputs.items():
            status = f"✅ {path.name}" if path else "❌ skipped"
            logger.info("  %s: %s", fmt.upper(), status)

        return outputs
