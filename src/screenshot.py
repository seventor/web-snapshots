from __future__ import annotations

import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

from config import AppConfig, UrlTarget

logger = logging.getLogger(__name__)


def capture_screenshots(config: AppConfig, output_dir: Path) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    saved_paths: list[Path] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--disable-dev-shm-usage",
                "--disable-gpu",
            ],
        )
        try:
            for target in config.urls:
                path = output_dir / f"{target.name}.jpg"
                _capture_target(browser, target, config, path)
                saved_paths.append(path)
                logger.info("Captured screenshot for %s -> %s", target.url, path)
        finally:
            browser.close()

    return saved_paths


def _capture_target(browser, target: UrlTarget, config: AppConfig, path: Path) -> None:
    context = browser.new_context(
        viewport={"width": target.viewport_width, "height": target.viewport_height},
        user_agent=(
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
    )
    page = context.new_page()
    try:
        page.goto(target.url, wait_until="networkidle", timeout=60_000)
        if target.wait_ms > 0:
            page.wait_for_timeout(target.wait_ms)
        page.screenshot(
            path=str(path),
            type="jpeg",
            quality=config.screenshot_quality,
            full_page=target.full_page,
        )
    finally:
        context.close()
