from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_env(env_path: Path | None = None) -> None:
    """Load .env file. In prod (Railway), vars are already injected — this is a no-op."""
    path = env_path or Path(__file__).parent.parent / ".env"
    load_dotenv(path, override=False)
