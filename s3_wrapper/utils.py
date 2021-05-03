import os

from typing import Any


class S3Utils(object):

    def __init__(self, LOCAL_TEST=False):
        if LOCAL_TEST:
            import localstack_client.session as boto3
        else:
            import boto3

        aws_profile = os.getenv('AWS_PROFILE_NAME', None)
        session = boto3.Session(profile_name=aws_profile)
        self._s3 = session.resource('s3')
        self._s3_client = self._s3.meta.client
        if os.getenv('S3_BUCKET_NAME'):
            self._default_bucket = self._s3.Bucket(os.getenv('S3_BUCKET_NAME'))
        self._default_bucket_name = os.getenv('S3_BUCKET_NAME')

    def get_bucket_name(self, bucket_name):
        return bucket_name if bucket_name is not None else self._default_bucket_name

    def get_bucket(self, bucket_name=None):
        if bucket_name:
            bucket = self._s3.Bucket(bucket_name)
        else:
            bucket = self._default_bucket
        return bucket

    def set_default_bucket(self, bucket_name: str):
        assert bucket_name and isinstance(bucket_name, str)
        self._default_bucket = self._s3.Bucket(bucket_name)
        self._default_bucket_name = bucket_name

    def move_object(self, old_key: str, new_key: str, bucket_name: str = None) -> bool:
        bucket_name = self.get_bucket_name(bucket_name)
        self._s3.Object(bucket_name, new_key).copy_from(
            CopySource=f"{bucket_name}/{old_key}")
        self._s3.Object(bucket_name, old_key).delete()

    def copy_object(self, new_obj_key: str, src_obj_key: str, bucket_name: str = None):
        bucket_name = self.get_bucket_name(bucket_name)
        self._s3.Object(bucket_name, new_obj_key).copy_from(
            CopySource=f'{bucket_name}/{src_obj_key}')

    def create_object(self, key: str, content: Any, bucket_name: str = None):
        bucket_name = self.get_bucket_name(bucket_name)
        s3_object = self._s3.Object(bucket_name, key)
        s3_object.put(Body=bytes(content, 'utf-8'))

    def upload_file(self, key: str, file_path: str, bucket_name: str = None):
        bucket = self.get_bucket(bucket_name)
        bucket.upload_file(file_path, key)

    def delete_object(self, key: str, bucket_name: str = None) -> bool:
        bucket = self.get_bucket(bucket_name)
        bucket.delete_objects(
            Delete={
                'Objects': [{'Key': key}]
            },
        )
        return True

    def delete_objects(self, keys: list, bucket_name: str = None) -> bool:
        bucket = self.get_bucket(bucket_name)
        bucket.delete_objects(
            Delete={
                'Objects': [{'Key': key} for key in keys]
            },
        )

    def find_files_with_prefix(self, prefix: str, bucket_name: str = None) -> list:
        bucket = self.get_bucket(bucket_name)
        objects = bucket.objects.filter(Prefix=prefix)
        return objects

    def generate_presigned_url(self, key: str, expiration: int, bucket_name: str = None) -> str:
        bucket_name = self.get_bucket_name(bucket_name)
        url = self._s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket_name, 'Key': key, },
            ExpiresIn=expiration
        )
        return url

    def download_file(self, key: str, file_path: str, bucket_name: str = None):
        bucket_name = self.get_bucket_name(bucket_name)
        self._s3_client.download_file(bucket_name, key, file_path)


    def download_write_to_file(self, key: str, file_io=None, bucket_name: str = None):
        bucket_name = self.get_bucket_name(bucket_name)
        self._s3_client.download_fileobj(bucket_name, key, file_io)

    def file_exists(self, key: str, bucket_name: str = None) -> bool:
        bucket_name = self.get_bucket_name(bucket_name)
        try:
            self._s3.Object(bucket_name, key).load()
            return True
        except:
            return False
