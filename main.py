import json
import pprint

from s3_wrapper import S3Utils
from io import BytesIO, StringIO
import uuid

LOCAL_TEST = True

if LOCAL_TEST:
    import localstack_client.session as boto3
else:
    import boto3

file = BytesIO()

client = boto3.client('s3')
response = client.list_buckets()
pprint.pprint(response)
bucket_name = '21342134e132123'
bucket = client.create_bucket(Bucket=bucket_name)
data = {
    'message': 'Hello world',
    'created_at': '2020-06-03 05:36:00'
}
formatted_data = json.dumps(data)
s3 = S3Utils(LOCAL_TEST=LOCAL_TEST)
s3.set_default_bucket(bucket_name=bucket_name)
s3.create_object(key='key', content=formatted_data, bucket_name=bucket_name)

s3.upload_file('key2', 't.txt')
exists = s3.file_exists('key2')
print(exists)
file = BytesIO()
s3.download_write_to_file('key2', file)
print(file.getvalue())
s3.download_file('key2', 't2.txt')


def create_temp_file(size, file_name, file_content):
    random_file_name = ''.join([str(uuid.uuid4().hex[:6]), file_name])
    with open(random_file_name, 'w') as f:
        f.write(str(file_content) * size)
    return random_file_name


session = boto3.Session()
s3_resource = session.resource('s3')
third_file_name = create_temp_file(300, 'thirdfile.txt', 't')
# bucket = client.create_bucket(Bucket=bucket_name)
third_object = s3_resource.Object(bucket_name, third_file_name)
third_object.upload_file(third_file_name, ExtraArgs={
    'ServerSideEncryption': 'AES256'})
