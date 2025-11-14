# app/core/s3.py
import boto3
from botocore.config import Config
from core.config import settings

def s3_client():
    # Ej.: s3.latam.digitaloceanspaces.com
    endpoint = settings.DO_SPACES_ENDPOINT.rstrip("/")
    is_spaces = "digitaloceanspaces.com" in endpoint

    cfg = Config(signature_version="s3v4", s3={"addressing_style": "virtual"})
    params = {
        "service_name": "s3",
        "endpoint_url": f"https://{endpoint}",
        "config": cfg,
    }
    # DO Spaces usa access/secret tipo S3:
    return boto3.client(
        **params,
        aws_access_key_id=settings.DO_ACCESS_KEY,
        aws_secret_access_key=settings.DO_SECRET_KEY,
        region_name=getattr(settings, "DO_REGION", None) or "us-east-1",
    )
