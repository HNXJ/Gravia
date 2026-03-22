"""Gravia configuration system.

Loads settings from ~/.gravia.toml, env vars, or CLI overrides.
"""

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

if sys.version_info >= (3, 11):
    import tomllib
else:
    try:
        import tomli as tomllib  # type: ignore[no-redef]
    except ImportError:
        tomllib = None  # type: ignore[assignment]


_DEFAULT_CONFIG_PATH = Path.home() / ".gravia.toml"


@dataclass
class RemoteConfig:
    """Remote VLM backend settings (M3 Max or compatible)."""
    host: str = "100.69.184.42"
    reasoning_port: int = 4474
    vision_port: int = 4476
    ssh_user: str = "HN"
    ssh_key: str = str(Path.home() / ".ssh" / "bridger_id_ed25519")
    model: str = "default_model"
    timeout: int = 600

    @property
    def reasoning_url(self) -> str:
        return f"http://{self.host}:{self.reasoning_port}/v1/chat/completions"

    @property
    def vision_url(self) -> str:
        return f"http://{self.host}:{self.vision_port}/v1/chat/completions"


@dataclass
class DeepReadConfig:
    """DeepRead engine settings."""
    max_chars: int = 40_000
    temperature: float = 0.2
    max_tokens: int = 4096
    retries: int = 3
    system_prompt: str = (
        "You are a senior neuroscience researcher. "
        "Extract the key findings and logic from the provided paper text."
    )


@dataclass
class WriterConfig:
    """Writer engine settings."""
    default_template: str = "biorxiv"
    compile_pdf: bool = False


@dataclass
class SlideTheaterConfig:
    """SlideTheater engine settings."""
    default_theme: str = "madelane"
    reveal_version: str = "4.3.1"
    transition: str = "convex"


@dataclass
class GraviaConfig:
    """Top-level Gravia configuration."""
    # Directories
    input_dir: Path = field(default_factory=lambda: Path.home() / "workspace" / "misc" / "papers" / "pdfs")
    output_dir: Path = field(default_factory=lambda: Path.home() / "workspace" / "misc" / "papers" / "markdowns")
    temp_dir: Path = field(default_factory=lambda: Path.home() / "workspace" / "misc" / "papers" / "deepread_temp")

    # Sub-configs
    remote: RemoteConfig = field(default_factory=RemoteConfig)
    deepread: DeepReadConfig = field(default_factory=DeepReadConfig)
    writer: WriterConfig = field(default_factory=WriterConfig)
    slidetheater: SlideTheaterConfig = field(default_factory=SlideTheaterConfig)

    # Logging
    verbose: bool = False

    @classmethod
    def load(cls, path: Optional[Path] = None) -> "GraviaConfig":
        """Load config from TOML file, falling back to defaults.

        Priority: env vars > TOML file > defaults.
        """
        config = cls()
        toml_path = path or _DEFAULT_CONFIG_PATH

        # Load TOML if it exists
        if toml_path.exists() and tomllib is not None:
            with open(toml_path, "rb") as f:
                data = tomllib.load(f)
            config = _merge_toml(config, data)

        # Override with env vars
        config = _apply_env_overrides(config)
        return config


def _merge_toml(config: GraviaConfig, data: dict) -> GraviaConfig:
    """Merge TOML data into config dataclass."""
    if "input_dir" in data:
        config.input_dir = Path(data["input_dir"])
    if "output_dir" in data:
        config.output_dir = Path(data["output_dir"])
    if "temp_dir" in data:
        config.temp_dir = Path(data["temp_dir"])
    if "verbose" in data:
        config.verbose = data["verbose"]

    if "remote" in data:
        r = data["remote"]
        for key in ("host", "reasoning_port", "vision_port", "ssh_user", "ssh_key", "model", "timeout"):
            if key in r:
                setattr(config.remote, key, r[key])

    if "deepread" in data:
        d = data["deepread"]
        for key in ("max_chars", "temperature", "max_tokens", "retries", "system_prompt"):
            if key in d:
                setattr(config.deepread, key, d[key])

    if "writer" in data:
        w = data["writer"]
        for key in ("default_template", "compile_pdf"):
            if key in w:
                setattr(config.writer, key, w[key])

    if "slidetheater" in data:
        s = data["slidetheater"]
        for key in ("default_theme", "reveal_version", "transition"):
            if key in s:
                setattr(config.slidetheater, key, s[key])

    return config


def _apply_env_overrides(config: GraviaConfig) -> GraviaConfig:
    """Override config fields from GRAVIA_* environment variables."""
    env_map = {
        "GRAVIA_INPUT_DIR": ("input_dir", Path),
        "GRAVIA_OUTPUT_DIR": ("output_dir", Path),
        "GRAVIA_REMOTE_HOST": ("remote.host", str),
        "GRAVIA_REMOTE_PORT": ("remote.reasoning_port", int),
        "GRAVIA_VERBOSE": ("verbose", lambda x: x.lower() in ("1", "true", "yes")),
    }
    for env_key, (attr_path, cast) in env_map.items():
        val = os.environ.get(env_key)
        if val is not None:
            parts = attr_path.split(".")
            obj = config
            for part in parts[:-1]:
                obj = getattr(obj, part)
            setattr(obj, parts[-1], cast(val))
    return config
