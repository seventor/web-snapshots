#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from dotenv import load_dotenv

from handler import run_task


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the screenshot task locally.")
    parser.add_argument(
        "--config",
        default=str(ROOT / "config.yaml"),
        help="Path to config.yaml",
    )
    parser.add_argument(
        "--output-dir",
        default=str(ROOT / "output"),
        help="Directory for saved screenshots when running locally",
    )
    args = parser.parse_args()

    load_dotenv(ROOT / ".env")
    os.environ.setdefault("CONFIG_PATH", args.config)
    os.environ.setdefault("LOCAL_OUTPUT_DIR", args.output_dir)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )

    result = run_task()
    print(f"Saved {result['count']} screenshot(s):")
    for url in result["urls"]:
        print(f"  - {url}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
