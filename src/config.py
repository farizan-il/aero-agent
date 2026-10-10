import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

# API Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()

# Model Configurations
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
FALLBACK_MODELS = ["gemini-3.5-flash", "gemini-3.8-flash", "gemini-flash-latest"]
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "models/text-embedding-004")
AGENT_TEMPERATURE = float(os.getenv("AGENT_TEMPERATURE", "0.3"))

# Paths
KNOWLEDGE_BASE_DIR = Path(os.getenv("KNOWLEDGE_BASE_DIR", str(BASE_DIR / "knowledge_base")))


def validate_config():
    """Validates required configurations and returns list of missing items."""
    missing = []
    if not GEMINI_API_KEY or GEMINI_API_KEY == "your_gemini_api_key_here":
        missing.append("GEMINI_API_KEY is not set or using placeholder value.")
    return missing
