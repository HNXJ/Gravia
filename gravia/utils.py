"""Shared utilities for Gravia modules."""

import logging
import subprocess
import sys
from pathlib import Path


def setup_logging(verbose: bool = False) -> logging.Logger:
    """Configure root logger with rich-style formatting.

    Args:
        verbose: If True, set DEBUG level. Otherwise INFO.

    Returns:
        Configured root logger for the gravia namespace.
    """
    level = logging.DEBUG if verbose else logging.INFO
    logger = logging.getLogger("gravia")

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        fmt = logging.Formatter(
            "%(asctime)s │ %(name)-20s │ %(levelname)-7s │ %(message)s",
            datefmt="%H:%M:%S",
        )
        handler.setFormatter(fmt)
        logger.addHandler(handler)

    logger.setLevel(level)
    return logger


def ensure_dir(path: Path) -> Path:
    """Create directory (and parents) if it doesn't exist. Returns the path."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_path(path: str | Path) -> Path:
    """Resolve a path to absolute, expanding ~ and env vars."""
    return Path(str(path)).expanduser().resolve()


def run_subprocess(
    cmd: list[str],
    cwd: Path | None = None,
    capture: bool = True,
    check: bool = False,
) -> subprocess.CompletedProcess:
    """Run a subprocess with proper error handling.

    Args:
        cmd: Command and arguments list.
        cwd: Working directory.
        capture: Whether to capture stdout/stderr.
        check: Whether to raise on non-zero exit.

    Returns:
        CompletedProcess instance.
    """
    logger = logging.getLogger("gravia.subprocess")
    logger.debug("Running: %s", " ".join(cmd))

    result = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=capture,
        text=True,
        check=check,
    )

    if result.returncode != 0 and capture:
        logger.warning("Command exited %d: %s", result.returncode, result.stderr[:500])

    return result
