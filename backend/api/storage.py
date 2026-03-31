import logging
import uuid

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from api.config import get_settings

logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Raised when an R2/S3 operation fails."""


def _get_s3_client():
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.r2_endpoint_url,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name="auto",
        config=Config(signature_version="s3v4"),
    )


def upload_audio(file_bytes: bytes, original_filename: str, job_id: str) -> str:
    settings = get_settings()
    ext = original_filename.rsplit(".", 1)[-1].lower()
    key = f"uploads/{job_id}/{uuid.uuid4().hex}.{ext}"
    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=settings.r2_bucket_name,
            Key=key,
            Body=file_bytes,
            ContentType=_content_type_for_ext(ext),
        )
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to upload audio for job %s: %s", job_id, exc)
        raise StorageError(f"Failed to upload audio: {exc}") from exc
    return key


def upload_result_file(file_bytes: bytes, job_id: str, filename: str) -> str:
    settings = get_settings()
    key = f"results/{job_id}/{filename}"
    try:
        s3 = _get_s3_client()
        s3.put_object(
            Bucket=settings.r2_bucket_name,
            Key=key,
            Body=file_bytes,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to upload result %s for job %s: %s", filename, job_id, exc)
        raise StorageError(f"Failed to upload result file: {exc}") from exc
    return key


def get_presigned_download_url(key: str, expires_in: int = 3600) -> str:
    try:
        s3 = _get_s3_client()
        settings = get_settings()
        return s3.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.r2_bucket_name, "Key": key},
            ExpiresIn=expires_in,
        )
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to generate presigned URL for %s: %s", key, exc)
        raise StorageError(f"Failed to generate download URL: {exc}") from exc


def download_from_r2(key: str) -> bytes:
    try:
        s3 = _get_s3_client()
        settings = get_settings()
        response = s3.get_object(Bucket=settings.r2_bucket_name, Key=key)
        return response["Body"].read()
    except (BotoCoreError, ClientError) as exc:
        logger.error("Failed to download %s from R2: %s", key, exc)
        raise StorageError(f"Failed to download from storage: {exc}") from exc


def _content_type_for_ext(ext: str) -> str:
    return {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "flac": "audio/flac",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
        "aac": "audio/aac",
    }.get(ext, "application/octet-stream")
