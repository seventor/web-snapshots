from __future__ import annotations

import logging
import mimetypes
import os
import shutil
from pathlib import Path

import boto3

from config import AppConfig

logger = logging.getLogger(__name__)


def persist_screenshots(config: AppConfig, files: list[Path]) -> list[str]:
    local_output_dir = os.environ.get("LOCAL_OUTPUT_DIR")
    if local_output_dir:
        return _save_locally(config, files, Path(local_output_dir))

    if not config.s3_bucket:
        raise ValueError(
            "S3_BUCKET is not configured. Set LOCAL_OUTPUT_DIR for local file output."
        )

    return _upload_to_s3(config, files)


def _save_locally(config: AppConfig, files: list[Path], output_dir: Path) -> list[str]:
    prefix_dir = output_dir / config.s3_prefix.strip("/")
    prefix_dir.mkdir(parents=True, exist_ok=True)
    public_urls: list[str] = []

    for file_path in files:
        destination = prefix_dir / file_path.name
        shutil.copy2(file_path, destination)
        public_url = f"{config.public_base_url}/{file_path.name}"
        public_urls.append(public_url)
        logger.info("Saved locally: %s", destination)

    return public_urls


def _upload_to_s3(config: AppConfig, files: list[Path]) -> list[str]:
    client = boto3.client("s3")
    public_urls: list[str] = []

    for file_path in files:
        key = f"{config.s3_prefix}{file_path.name}"
        content_type = mimetypes.guess_type(file_path.name)[0] or "image/jpeg"
        client.upload_file(
            str(file_path),
            config.s3_bucket,
            key,
            ExtraArgs={"ContentType": content_type},
        )
        public_url = f"{config.public_base_url}/{file_path.name}"
        public_urls.append(public_url)
        logger.info("Uploaded s3://%s/%s", config.s3_bucket, key)

    return public_urls
