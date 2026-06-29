from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class UrlTarget:
    url: str
    name: str
    viewport_width: int
    viewport_height: int
    wait_ms: int
    full_page: bool


@dataclass(frozen=True)
class AppConfig:
    urls: list[UrlTarget]
    screenshot_format: str
    screenshot_quality: int
    s3_bucket: str
    s3_prefix: str
    public_base_url: str
    schedule_rate_minutes: int


def _default_config_path() -> Path:
    env_path = os.environ.get("CONFIG_PATH")
    if env_path:
        return Path(env_path)
    return Path(__file__).resolve().parent.parent / "config.yaml"


def load_config(path: Path | None = None) -> AppConfig:
    config_path = path or _default_config_path()
    with config_path.open(encoding="utf-8") as handle:
        raw: dict[str, Any] = yaml.safe_load(handle) or {}

    urls: list[UrlTarget] = []
    for entry in raw.get("urls", []):
        viewport = entry.get("viewport", {})
        urls.append(
            UrlTarget(
                url=entry["url"],
                name=entry["name"],
                viewport_width=int(viewport.get("width", 1920)),
                viewport_height=int(viewport.get("height", 1080)),
                wait_ms=int(entry.get("wait_ms", 2000)),
                full_page=bool(entry.get("full_page", False)),
            )
        )

    screenshot = raw.get("screenshot", {})
    storage = raw.get("storage", {})
    schedule = raw.get("schedule", {})

    s3_bucket = os.environ.get("S3_BUCKET") or storage.get("s3_bucket", "")
    s3_prefix = os.environ.get("S3_PREFIX") or storage.get("s3_prefix", "snapshots/")
    public_base_url = (
        os.environ.get("PUBLIC_BASE_URL")
        or storage.get("public_base_url", "")
        or "https://grense.land/snapshots"
    )

    return AppConfig(
        urls=urls,
        screenshot_format=screenshot.get("format", "jpeg"),
        screenshot_quality=int(screenshot.get("quality", 85)),
        s3_bucket=s3_bucket,
        s3_prefix=_normalize_prefix(s3_prefix),
        public_base_url=public_base_url.rstrip("/"),
        schedule_rate_minutes=int(schedule.get("rate_minutes", 5)),
    )


def _normalize_prefix(prefix: str) -> str:
    normalized = prefix.strip("/")
    return f"{normalized}/" if normalized else ""
