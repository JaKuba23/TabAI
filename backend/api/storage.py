import uuid

import boto3
from botocore.config import Config

from api.config import get_settings


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
    s3 = _get_s3_client()
    settings = get_settings()
    ext = original_filename.rsplit(".", 1)[-1].lower()
    key = f"uploads/{job_id}/{uuid.uuid4().hex}.{ext}"
    s3.put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=file_bytes,
        ContentType=_content_type_for_ext(ext),
    )
    return key


def upload_result_file(file_bytes: bytes, job_id: str, filename: str) -> str:
    s3 = _get_s3_client()
    settings = get_settings()
    key = f"results/{job_id}/{filename}"
    s3.put_object(
        Bucket=settings.r2_bucket_name,
        Key=key,
        Body=file_bytes,
    )
    return key


def get_presigned_download_url(key: str, expires_in: int = 3600) -> str:
    s3 = _get_s3_client()
    settings = get_settings()
    return s3.generate_presigned_url(
        "get_object",
        Params={"Bucket": settings.r2_bucket_name, "Key": key},
        ExpiresIn=expires_in,
    )


def download_from_r2(key: str) -> bytes:
    s3 = _get_s3_client()
    settings = get_settings()
    response = s3.get_object(Bucket=settings.r2_bucket_name, Key=key)
    return response["Body"].read()


def _content_type_for_ext(ext: str) -> str:
    return {
        "mp3": "audio/mpeg",
        "wav": "audio/wav",
        "flac": "audio/flac",
        "m4a": "audio/mp4",
        "ogg": "audio/ogg",
        "aac": "audio/aac",
    }.get(ext, "application/octet-stream")
