"""Configuration helpers for Aero Scout."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv


def load_environment() -> None:
    """Load environment variables from the package-local .env file."""
    load_dotenv(dotenv_path=Path(__file__).with_name(".env"))
