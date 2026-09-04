from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]

@dataclass(frozen=True)
class Settings:
    seoul_key: str
    supabase_url: str
    supabase_service_key: str
    target_district: str = "송파구"
    page_size: int = 1000

    @classmethod
    def from_env(cls) -> "Settings":
        load_dotenv(ROOT / ".env.local")
        required = {name: os.getenv(name, "" ).strip() for name in ("SEOUL_OPEN_API_KEY", "SUPABASE_SERVICE_ROLE_KEY")}
        required["SUPABASE_URL"] = (os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL") or "").strip()
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise RuntimeError("필수 환경변수 누락: " + ", ".join(missing))
        return cls(required["SEOUL_OPEN_API_KEY"], required["SUPABASE_URL"].rstrip("/"), required["SUPABASE_SERVICE_ROLE_KEY"], os.getenv("TARGET_DISTRICT", "송파구"))
