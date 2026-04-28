"""DeepRead engine: PDF → VLM analysis → structured Markdown.

Refactored from legacy deepread.py with:
- Class-based engine with config injection
- Async HTTP (httpx) for parallel batch processing
- Structured error handling with exponential backoff
- PaperAnalysis dataclass return type
- Proper logging throughout
"""

import asyncio
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import fitz  # PyMuPDF
import httpx
from PIL import Image

from gravia.config import GraviaConfig
from gravia.utils import ensure_dir

# Allow oversized images (scientific figures can be huge)
Image.MAX_IMAGE_PIXELS = None

logger = logging.getLogger("gravia.deepread")


@dataclass
class PaperAnalysis:
    """Structured output from DeepRead analysis."""
    title: str = "Untitled Research Paper"
    doi: str = "Unknown DOI"
    source_path: Path = field(default_factory=lambda: Path("."))
    full_text: str = ""
    analysis_content: str = ""
    success: bool = False
    error: Optional[str] = None

    @property
    def markdown(self) -> str:
        """Compile the final Markdown report."""
        return (
            f"# {self.title}\n\n"
            f"**DOI**: {self.doi}\n\n"
            f"---\n\n"
            f"{self.analysis_content}"
        )


class DeepReadEngine:
    """Async VLM-powered paper analysis engine.

    Usage:
        engine = DeepReadEngine(config)
        result = await engine.process_paper(Path("paper.pdf"))
        # or batch:
        results = await engine.process_batch(Path("papers/"))
    """

    def __init__(self, config: GraviaConfig):
        self.config = config
        self.rc = config.remote
        self.dc = config.deepread

    # -- Text Extraction --

    @staticmethod
    def extract_text(file_path: Path) -> str:
        """Extract raw text from PDF using PyMuPDF."""
        logger.debug("Extracting text from %s", file_path.name)
        text = ""
        doc = fitz.open(str(file_path))
        for page in doc:
            text += page.get_text()
        doc.close()
        return text

    @staticmethod
    def extract_metadata(text: str) -> tuple[str, str]:
        """Extract title and DOI from raw text via regex heuristics.

        Returns:
            (title, doi) tuple with best-effort extraction.
        """
        # DOI extraction
        doi_match = re.search(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', text, re.I)
        doi = doi_match.group(0) if doi_match else "Unknown DOI"

        # Title heuristic: first substantive line (>20 chars)
        lines = [ln.strip() for ln in text.split('\n') if len(ln.strip()) > 20]
        title = lines[0] if lines else "Untitled Research Paper"

        return title, doi

    def _build_prompt(self, title: str, doi: str) -> str:
        """Build the analysis prompt for the VLM."""
        return (
            f"Analyze this scientific content carefully.\n"
            f"Title: {title}\n"
            f"DOI: {doi}\n\n"
            f"Tasks:\n"
            f"1. Study Summary: State the hypothesis, main finding, and significance in 3-4 bullet points.\n"
            f"2. Figure Breakdown: For each major figure, describe the analysis and result.\n"
            f"3. Implementation Logic: High-level step-by-step logic for re-implementing figures in Python.\n"
            f"4. Expected Controls: What statistical controls are mentioned or necessary?\n\n"
            f"Provide the response in structured Markdown."
        )

    # -- VLM Inference --

    async def _call_vlm(self, prompt: str, paper_text: str, model: Optional[str] = None) -> str:
        """Delegate VLM call to the Sovereign Orchestrator.
        
        Args:
            prompt: The analysis prompt.
            paper_text: Truncated paper text content.
            model: Optional model override.
        """
        from gravia.orchestrator.manager import sov_orchestrator
        
        target_model = model or self.rc.model
        payload = prompt
        if paper_text:
            payload += f"\n\nPaper Text:\n{paper_text}"
        return await sov_orchestrator.delegate(payload, target_model)

    # -- Paper Processing --

    async def process_paper(self, file_path: Path) -> PaperAnalysis:
        """Process a single PDF into a structured analysis with chunked summarization.

        Args:
            file_path: Path to the PDF file.

        Returns:
            PaperAnalysis with results or error information.
        """
        file_path = Path(file_path).resolve()
        analysis = PaperAnalysis(source_path=file_path)

        logger.info("📖 Processing: %s", file_path.name)

        try:
            # Extract text
            analysis.full_text = self.extract_text(file_path)
            analysis.title, analysis.doi = self.extract_metadata(analysis.full_text)

            # Chunking Logic: Process in blocks of ~max_chars to avoid OOM
            chunk_size = self.dc.max_chars
            chunks = [analysis.full_text[i:i + chunk_size] for i in range(0, len(analysis.full_text), chunk_size)]
            
            partial_summaries = []
            for idx, chunk in enumerate(chunks):
                logger.info("🧠 Analyzing Chunk %d/%d for: %s", idx + 1, len(chunks), analysis.title[:30])
                chunk_prompt = (
                    f"Summarize this section of the paper titled '{analysis.title}'.\n"
                    f"Focus on: {idx+1}/{len(chunks)}\n\n"
                    f"Content:\n{chunk}"
                )
                summary = await self._call_vlm(chunk_prompt, "")
                partial_summaries.append(summary)

            # Final Synthesis
            logger.info("🎨 Synthesizing final report...")
            synthesis_prompt = (
                f"Synthesize the following partial summaries into a professional research report for '{analysis.title}'.\n"
                f"Include Summary, Figure Breakdowns (if mentioned), and Implementation Logic.\n\n"
                f"Summaries:\n" + "\n\n".join(partial_summaries)
            )
            analysis.analysis_content = await self._call_vlm(synthesis_prompt, "", model=self.rc.synthesis_model)
            analysis.success = True
            logger.info("✅ Analysis complete for: %s", analysis.title[:60])

        except Exception as e:
            analysis.error = str(e)
            analysis.success = False
            logger.error("❌ Failed to process %s: %s", file_path.name, e)

        return analysis

    async def process_batch(
        self,
        input_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        max_concurrent: int = 3,
    ) -> list[PaperAnalysis]:
        """Process all PDFs in a directory with controlled concurrency.

        Args:
            input_dir: Directory containing PDFs. Falls back to config.
            output_dir: Directory for output Markdowns. Falls back to config.
            max_concurrent: Maximum parallel VLM requests.

        Returns:
            List of PaperAnalysis results.
        """
        input_dir = input_dir or self.config.input_dir
        output_dir = output_dir or self.config.output_dir
        ensure_dir(output_dir)

        pdfs = sorted(input_dir.glob("*.pdf"))
        logger.info("🚀 Found %d papers in %s", len(pdfs), input_dir)

        # Filter already-processed
        pending = [
            p for p in pdfs
            if not (output_dir / f"{p.stem}_analysis.md").exists()
        ]
        skipped = len(pdfs) - len(pending)
        if skipped:
            logger.info("⏭️  Skipping %d already-analyzed papers", skipped)

        # Process with semaphore for concurrency control
        semaphore = asyncio.Semaphore(max_concurrent)
        results: list[PaperAnalysis] = []

        async def _bounded_process(pdf: Path) -> PaperAnalysis:
            async with semaphore:
                result = await self.process_paper(pdf)
                if result.success:
                    out_path = output_dir / f"{pdf.stem}_analysis.md"
                    out_path.write_text(result.markdown, encoding="utf-8")
                    logger.info("💾 Saved: %s", out_path.name)
                return result

        tasks = [_bounded_process(pdf) for pdf in pending]
        results = await asyncio.gather(*tasks)
        
        succeeded = sum(1 for r in results if r.success)
        logger.info("📊 Batch complete: %d/%d succeeded", succeeded, len(results))
        return list(results)
