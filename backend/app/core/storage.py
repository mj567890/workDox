from datetime import timedelta
from io import BytesIO
from typing import Optional

from minio import Minio
from minio.error import S3Error

from app.config import get_settings

settings = get_settings()


class MinIOClient:
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self._ensure_bucket()

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

    def get_presigned_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        try:
            return self.client.presigned_get_object(
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
