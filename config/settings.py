from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    gemini_api_key: str
    hf_token: str
    wp_base_url: str
    wp_username: str
    wp_password: str


def load_settings() -> Settings:
    load_dotenv()
    return Settings(
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        hf_token=os.getenv("HF_TOKEN", "").strip(),
        wp_base_url=os.getenv("WP_BASE_URL", "").strip(),
        wp_username=os.getenv("WP_USERNAME", "").strip(),
        wp_password=os.getenv("WP_PASSWORD", "").strip(),
    )
