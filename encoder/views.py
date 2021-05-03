from django.http import HttpResponse
from django.shortcuts import render
import json
from s3_wrapper import S3Utils


def encoder_view(request):
    do_encode_test()
    return HttpResponse('boom')


def do_encode_test():
    bucket_name = 'zappa-encode'
    data = {
        'message': 'Hello world',
        'created_at': '2020-06-03 05:36:00'
    }
    formatted_data = json.dumps(data)
    s3 = S3Utils()
    s3.set_default_bucket(bucket_name=bucket_name)
    s3.create_object(key='boom_key', content=formatted_data, bucket_name=bucket_name)
