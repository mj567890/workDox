from datetime import timedelta
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import get_settings

settings = get_settings()


class MinIOClient:
    def __init__(self):
        self._endpoint = settings.MINIO_ENDPOINT
        self.client = Minio(
            endpoint=self._endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

        # Secondary client for public-facing presigned URLs
        # (signing is local, no network call needed)
        self._public_endpoint = settings.MINIO_PUBLIC_ENDPOINT
        if self._public_endpoint and self._public_endpoint != self._endpoint:
            self._public_client = Minio(
                endpoint=self._public_endpoint,
                access_key=settings.MINIO_ACCESS_KEY,
                secret_key=settings.MINIO_SECRET_KEY,
                secure=settings.MINIO_SECURE,
            )
        else:
            self._public_client = None

    def _ensure_bucket(self):
        if not self.client.bucket_exists(self.bucket):
            self.client.make_bucket(self.bucket)

    def upload_file(self, object_name: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(
            bucket_name=self.bucket,
            object_name=object_name,
            data=BytesIO(data),
            length=len(data),
            content_type=content_type,
        )
        return object_name

    def download_file(self, object_name: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(bucket_name=self.bucket, object_name=object_name)
            data = response.read()
            response.close()
            response.release_conn()
            return data
        except S3Error:
            return None

    def get_presigned_url(self, object_name: str, expires: int = 900) -> Optional[str]:
        """Generate a presigned URL for browser access.

        Uses the public endpoint if configured, so the URL is reachable
        from the user's browser (not just inside Docker network).

        Default TTL is 15 minutes (900s). Download links may request longer
        if needed (e.g. 3600s for large downloads).
        """
        try:
            signer = self._public_client or self.client
            return signer.presigned_get_object(
                bucket_name=self.bucket,
                object_name=object_name,
                expires=timedelta(seconds=expires),
            )
        except S3Error:
            return None

    def delete_file(self, object_name: str) -> bool:
        try:
            self.client.remove_object(bucket_name=self.bucket, object_name=object_name)
            return True
        except S3Error:
            return False

    def file_exists(self, object_name: str) -> bool:
        try:
            self.client.stat_object(bucket_name=self.bucket, object_name=object_name)
            return True
        except S3Error:
            return False


minio_client = MinIOClient()
