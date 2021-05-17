from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
import json
from Enkrypt import Dcryptor, Encryptor

from django.views.decorators.csrf import csrf_exempt

from s3_wrapper import S3Utils
from django import forms
from datetime import datetime


class DecodeForm(forms.Form):
    data = forms.CharField(max_length=100)

    def clean_data(self):
        data = self.cleaned_data['data']
        data = decode_string(data)
        return data


class EncodeForm(forms.Form):
    data = forms.CharField(max_length=100)

    def clean_data(self):
        data = self.cleaned_data['data']
        data = encode_string(data)
        return data


def encode_string(data):
    return data[::-1]


def decode_string(data):
    return data[::-1]


@csrf_exempt
def encoder_view(request):
    if request.method == 'POST':
        form = EncodeForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data['data']
            now_key = str(datetime.now())[-4:]
            save_data(data=data, key=now_key)
            return HttpResponse(now_key)
        return HttpResponse('nok post')
    if request.method == 'GET':
        key = request.GET.get('key')
        data = load_data(key=key)
        raw_data = json.loads(data)
        decoded_data = decode_string(raw_data.get('message'))
        return HttpResponse(decoded_data)
    return HttpResponse('nok')


def get_from_datastore(key):
    data = load_data(key=key)
    raw_data = json.loads(data)
    decoded_data = decode_string(raw_data.get('message'))
    return decoded_data


def save_data(bucket_name='zappa-encode', key='key', data='boom!'):
    now = datetime.now()
    enc = Encryptor(input_filename='tests.py', output_filename='tests.py.encrypted')
    enc.do_encryption()
    with open(file='tests.py.encrypted', mode='rb') as file:
        formatted_data = file.read()
    s3 = S3Utils()
    s3.set_default_bucket(bucket_name=bucket_name)
    s3.create_object(key=key, content=formatted_data, bucket_name=bucket_name)


def load_data(bucket_name='zappa-encode', key='key'):
    s3 = S3Utils()
    s3.set_default_bucket(bucket_name=bucket_name)
    data = s3.get_object(key=key)
    return data


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
