from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parent.parent
load_dotenv(ROOT_DIR / ".env")


OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL_DEFAULT = os.getenv("OPENROUTER_MODEL", "google/gemma-4-31b-it")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

MODEL_OPTIONS: dict[str, str] = {
    "ChatGPT": "openai/gpt-4o",
    "Gemini": "google/gemini-2.0-flash-001",
    "Claude": "anthropic/claude-3.5-sonnet",
    "Gemma": OPENROUTER_MODEL_DEFAULT,
}

SQLITE_PATH = ROOT_DIR / "database" / "chat.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///{SQLITE_PATH}"
