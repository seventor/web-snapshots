from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any

from config import load_config
from screenshot import capture_screenshots
from storage import persist_screenshots

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_task() -> dict[str, Any]:
    config = load_config()
    if not config.urls:
        raise ValueError("No URLs configured in config.yaml")

    with tempfile.TemporaryDirectory() as temp_dir:
        files = capture_screenshots(config, Path(temp_dir))
        public_urls = persist_screenshots(config, files)

    return {
        "count": len(public_urls),
        "urls": public_urls,
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    logger.info("Starting screenshot task, event=%s", event)
    result = run_task()
    logger.info("Screenshot task completed: %s", result)
    return result
