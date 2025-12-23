from datetime import timedelta
from core.config import config
from minio import Minio
from minio.helpers import ObjectWriteResult
from typing import Self
import json
from urllib.parse import urlsplit, urlunsplit


class MinioStorage:

    _instance: Self = None

    def __new__(cls: Self) -> Self:
        """
        `MinioStorage` class the main entrypoint to use minio

        ##  Example
        ```python
        from infrastructure.minio import MinioStorage

        minioStorage = MinioStorage()
        ```
        """
        if cls._instance == None:
            cls._instance = super().__new__(cls)
            cls._instance.__connect()
        return cls._instance

    def __connect(self) -> None:
        # Internal client for actual S3 operations (file uploads, bucket management, etc.)
        self.client = Minio(
            config.MINIO_ENDPOINT,
            access_key=config.MINIO_ACCESS_KEY,
            secret_key=config.MINIO_SECRET_KEY,
            secure=False,
            region="us-east-1",  # Set default region to avoid network calls for region lookup
        )
        
        # External client for generating presigned URLs that will work from browser
        # Uses external endpoint (localhost:9001) so signatures match when browser accesses
        if config.MINIO_EXTERNAL_ENDPOINT:
            self.external_client = Minio(
                config.MINIO_EXTERNAL_ENDPOINT,
                access_key=config.MINIO_ACCESS_KEY,
                secret_key=config.MINIO_SECRET_KEY,
                secure=getattr(config, 'MINIO_EXTERNAL_SECURE', False),
                region="us-east-1",  # Set default region to avoid network calls for region lookup
            )
        else:
            self.external_client = None
            
        self.public_bucket = config.MINIO_PUBLIC_BUCKET
        self.private_bucket = config.MINIO_PRIVATE_BUCKET

    def setup_buckets(self):
        # This policy allows anyone to read objects from the public bucket
        public_read_policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{self.public_bucket}/*"],
                },
            ],
        }

        # Ensure the public bucket exists and set its policy
        if not self.client.bucket_exists(self.public_bucket):
            self.client.make_bucket(self.public_bucket)
        self.client.set_bucket_policy(self.public_bucket, json.dumps(public_read_policy))

        # Ensure the private bucket exists
        if not self.client.bucket_exists(self.private_bucket):
            self.client.make_bucket(self.private_bucket)

    def bucket_exists(self, bucket_name) -> bool:
        """
        Check if the bucket exists

        :param bucket_name: Name of the bucket
        """
        found = self.client.bucket_exists(bucket_name)
        if not found:
            return False
        return True

    def create_bucket(self, bucket_name, location: str | None = None, object_lock: bool = False,) -> None:
        """
        Create a bucket with given name and region and object lock

        :param bucket_name: Name of the bucket.
        :param location: Region in which the bucket will be created.
        :param object_lock: Flag to set object-lock feature.

        """
        self.client.make_bucket(bucket_name, location, object_lock)

    def put_object(self, bucket_name, object_name, data, length, content_type="application/octet-stream", metadate=None,
                   sse=None, progress=None, part_size=0, num_parallel_uploads=3, tags=None, retention=None, legal_hold=False) -> ObjectWriteResult:
        """
        Uploads data from a stream to an object in a bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param data: An object having callable read() returning bytes object.
        :param length: Data size; -1 for unknown size and set valid part_size.
        :param content_type: Content type of the object.
        :param metadata: Any additional metadata to be uploaded along
            with your PUT request.
        :param sse: Server-side encryption.
        :param progress: A progress object;
        :param part_size: Multipart part size.
        :param num_parallel_uploads: Number of parallel uploads.
        :param tags: :class:`Tags` for the object.
        :param retention: :class:`Retention` configuration object.
        :param legal_hold: Flag to set legal hold for the object.
        :return: :class:`ObjectWriteResult` object.
        """
        if not self.bucket_exists(bucket_name=bucket_name):
            self.create_bucket(bucket_name=bucket_name)
        return self.client.put_object(bucket_name, object_name, data, length, content_type, metadate, sse, progress, part_size,
                                      num_parallel_uploads, tags, retention, legal_hold)

    def get_presigned_url(self, method, bucket_name, object_name, expires=timedelta(days=7), response_headers=None, request_date=None,
                          version_id=None, extra_query_params=None) -> str:
        """
        Get presigned URL of an object for HTTP method, expiry time and custom
        request parameters.

        :param method: HTTP method.
        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :param expires: Expiry in seconds; defaults to 7 days.
        :param response_headers: Optional response_headers argument to
                                 specify response fields like date, size,
                                 type of file, data about server, etc.
        :param request_date: Optional request_date argument to
                             specify a different request date. Default is
                             current date.
        :param version_id: Version ID of the object.
        :param extra_query_params: Extra query parameters for advanced usage.
        :return: URL string.
        """
        # Use external client for presigned URLs if configured
        # This ensures the signature matches the host the browser will access
        # The external client has region set, so it won't make network calls
        client = self.external_client if self.external_client else self.client
        
        return client.get_presigned_url(
            method,
            bucket_name,
            object_name,
            expires,
            response_headers,
            request_date,
            version_id,
            extra_query_params,
        )

    def get_url(self, bucket_name, object_name):
        return f"{config.MINIO_URL}/{bucket_name}/{object_name}"

    def remove_object(self, bucket_name, object_name):
        """
        Remove an object from a bucket.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        """
        return self.client.remove_object(bucket_name, object_name)

    def get_object(self, bucket_name: str, object_name: str):
        """
        Get an object from a bucket. Returns a response object that can be read/streamed.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :return: urllib3.response.HTTPResponse object with file data.
        """
        return self.client.get_object(bucket_name, object_name)

    def stat_object(self, bucket_name: str, object_name: str):
        """
        Get object metadata without downloading the object.

        :param bucket_name: Name of the bucket.
        :param object_name: Object name in the bucket.
        :return: Object metadata including size, content_type, etc.
        """
        return self.client.stat_object(bucket_name, object_name)


minioStorage = MinioStorage()
