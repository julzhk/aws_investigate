from typing import BinaryIO

from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
import os
import io

# see https://nitratine.net/blog/post/python-gcm-encryption-tutorial/
from s3_wrapper import S3Utils


class EncryptorBase:
    BUFFER_SIZE = 1024 * 1024  # The size in bytes that we read, encrypt and write to at once
    password = "password"
    SALT_LENGTH = 32
    NONCE_LENGTH = 16
    TAG_LENGTH = 16
    salt = get_random_bytes(SALT_LENGTH)
    key = scrypt(password, salt, key_len=32, N=2 ** 17, r=8, p=1)
    file_in = None
    file_out = None

    def __init__(self, input_filename='', output_filename='', input_string=''):
        self.cipher = AES.new(self.key, AES.MODE_GCM)
        self.output_filename = output_filename
        self.input_filename = input_filename
        if input_filename or output_filename:
            self.outputfilestream = open(self.output_filename, 'wb')
            self.inputfilestream = open(self.input_filename, 'rb')
        else:
            self.outputfilestream = io.BytesIO()
            self.inputfilestream = io.BytesIO()
            try:
                self.inputfilestream.write(input_string.encode('utf-8'))
            except AttributeError:
                self.inputfilestream.write(input_string)
            self.inputfilestream.seek(0)

    def read_file_in(self, file_in):
        self.salt = file_in.read(self.SALT_LENGTH)  # The salt we generated was 32 bits long
        nonce = file_in.read(self.NONCE_LENGTH)
        self.cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)

    def return_encryption(self, file_out):
        try:
            return file_out.getvalue()
        except AttributeError:
            pass


class Encryptor(EncryptorBase):
    def __init__(self, *args, **kwargs):
        super(Encryptor, self).__init__(*args, **kwargs)
        self.nonce = self.cipher.nonce

    def write_header(self, file_out):
        file_out.write(self.salt)
        file_out.write(self.nonce)

    def write_body(self, file_in, file_out):
        while len(data := file_in.read(self.BUFFER_SIZE)):
            encrypted_data = self.cipher.encrypt(data)
            file_out.write(encrypted_data)

    def write_footer(self, file_out):
        tag = self.cipher.digest()
        assert len(tag) == self.TAG_LENGTH
        file_out.write(tag)

    def do_encryption(self):
        with self.outputfilestream as file_out, \
                self.inputfilestream as file_in:
            self.write_header(file_out)
            self.write_body(file_in, file_out)
            self.write_footer(file_out)
            return self.return_encryption(file_out)


class Dcryptor(EncryptorBase):

    def __init__(self, *args, **kwargs):
        super(Dcryptor, self).__init__(*args, **kwargs)
        try:
            self.file_in_size = self.inputfilestream.getbuffer().nbytes
        except AttributeError:
            self.file_in_size = os.path.getsize(self.input_filename)
        self.encrypted_data_size = self.file_in_size - self.SALT_LENGTH - self.NONCE_LENGTH - self.TAG_LENGTH

    def verify(self, file_in):
        # Verify encrypted file is correct; assume we seek to the location of the tag
        tag = file_in.read(self.TAG_LENGTH)
        self.cipher.verify(tag)

    def read_and_output(self, file_in, file_out):
        for chunk_size in RangeAndRemainder(self.encrypted_data_size, self.BUFFER_SIZE):
            self.read_decrypt_write(chunk_size, file_in, file_out)

    def read_decrypt_write(self, chunk_size, file_in, file_out):
        data = file_in.read(chunk_size)
        decrypted_data = self.cipher.decrypt(data)
        file_out.write(decrypted_data)

    def do_decryption(self):
        with self.outputfilestream as file_out, \
                self.inputfilestream as file_in:
            self.read_file_in(file_in)
            self.read_and_output(file_in, file_out)
            self.verify(file_in)
            return self.return_encryption(file_out).decode()


def RangeAndRemainder(whole, chunk):
    # yields equal chunks, then finishes with the remainder
    quotent, remainder = divmod(whole, chunk)
    for _ in range(quotent):
        yield chunk
    yield remainder


s3 = S3Utils()
s3.set_default_bucket(bucket_name='zappa-encode')


def encode_string_then_decode():
    input_string = 'testencrypt'
    encrpyted = Encryptor(input_string=input_string).do_encryption()
    final_str = Dcryptor(input_string=encrpyted).do_decryption()
    assert (input_string == final_str)


encode_string_then_decode()


def upload_downloader():
    s3 = S3Utils()
    s3.set_default_bucket(bucket_name='zappa-encode')
    key = 'upload_download.txt'
    s3.upload_file(key=key, file_path='t2.txt')
    s3.download_file(key=key, file_path='t2_downloaded.txt')
    with open('t2.txt', 'rb') as t2, open('t2_downloaded.txt', 'rb') as t2b:
        assert (t2.read() == t2b.read())


upload_downloader()


def encode_string_upload_then_download():
    input_string = b'testencrypt'
    input_fn = 'src3.txt'
    with open('%s' % input_fn, 'wb') as src:
        src.write(input_string)
    encrpyt3 = 'src3.txt.encrpyted'
    Encryptor(input_filename=input_fn, output_filename=encrpyt3).do_encryption()
    s3.upload_file(key=encrpyt3, file_path=encrpyt3)
    file4 = 'downloadsrc3.txt.encrpyted'
    s3.download_file(key=encrpyt3, file_path=file4)
    with open(encrpyt3, 'rb') as t1, open(file4, 'rb') as t2:
        t1b, t2b = t1.read(), t2.read()
        assert (t1b == t2b)


encode_string_upload_then_download()


def encode_string_upload_then_download_then_decode():
    input_string = b'testencrypt'
    input_fn = 'src3.txt'
    with open('%s' % input_fn, 'wb') as src:
        src.write(input_string)
    encrpyt3 = 'src3.txt.encrpyted'
    Encryptor(input_filename=input_fn, output_filename=encrpyt3).do_encryption()
    s3.upload_file(key=encrpyt3, file_path=encrpyt3)
    file4 = 'downloadsrc4.txt.encrpyted'
    file5_clear = 'file5_clear.txt'
    s3.download_file(key=encrpyt3, file_path=file4)
    Dcryptor(input_filename=file4, output_filename=file5_clear).do_decryption()
    with open(file5_clear, 'rb') as t1, open(input_fn, 'rb') as t2:
        t1b, t2b = t1.read(), t2.read()
        assert (t1b == t2b)


event = {'body': 'testencrypt', 'headers': {'Accept': '*/*', 'Accept-Encoding': 'gzip, deflate', 'Connection': 'keep-alive', 'Content-Length': '11', 'Host': '127.0.0.1:3000',
                                            'User-Agent': 'python-requests/2.25.1', 'X-Forwarded-Port': '3000', 'X-Forwarded-Proto': 'http'}, 'httpMethod': 'POST', 'isBase64Encoded': False,
         'multiValueHeaders': {'Accept': ['*/*'], 'Accept-Encoding': ['gzip, deflate'], 'Connection': ['keep-alive'], 'Content-Length': ['11'], 'Host': ['127.0.0.1:3000'],
                               'User-Agent': ['python-requests/2.25.1'], 'X-Forwarded-Port': ['3000'], 'X-Forwarded-Proto': ['http']}, 'multiValueQueryStringParameters': None, 'path': '/hello',
         'pathParameters': None, 'queryStringParameters': None,
         'requestContext': {'accountId': '123456789012', 'apiId': '1234567890', 'domainName': '127.0.0.1:3000', 'extendedRequestId': None, 'httpMethod': 'POST',
                            'identity': {'accountId': None, 'apiKey': None, 'caller': None, 'cognitoAuthenticationProvider': None, 'cognitoAuthenticationType': None, 'cognitoIdentityPoolId': None,
                                         'sourceIp': '127.0.0.1', 'user': None, 'userAgent': 'Custom User Agent String', 'userArn': None}, 'path': '/hello', 'protocol': 'HTTP/1.1',
                            'requestId': 'bab73187-bc8d-48b4-9d72-065886b23467', 'requestTime': '16/May/2021:11:37:04 +0000', 'requestTimeEpoch': 1621165024, 'resourceId': '123456',
                            'resourcePath': '/hello', 'stage': 'Prod'}, 'resource': '/hello', 'stageVariables': None, 'version': '1.0'}
