"""Environment-based Gemini configuration."""
from dataclasses import dataclass
import os

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    gemini_model: str
    mongodb_uri: str = ""
    mongodb_database: str = "ai_sales_qualification"
    mongodb_collection: str = "conversations"


def get_settings() -> Settings:
    load_dotenv()
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash").strip(),
        mongodb_uri=os.getenv("MONGODB_URI", "").strip(),
        mongodb_database=os.getenv("MONGODB_DATABASE", "ai_sales_qualification").strip() or "ai_sales_qualification",
        mongodb_collection=os.getenv("MONGODB_COLLECTION", "conversations").strip() or "conversations",
    )


def require_api_key(settings: Settings) -> None:
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is missing. Copy .env.example to .env and add "
            "your Gemini API key from Google AI Studio."
        )
