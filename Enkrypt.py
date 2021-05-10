from Crypto.Random import get_random_bytes
from Crypto.Cipher import AES
from Crypto.Protocol.KDF import scrypt
import os


# see https://nitratine.net/blog/post/python-gcm-encryption-tutorial/


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

    def __init__(self, input_filename='t.txt', output_filename='t.txt.encrypted'):
        self.cipher = AES.new(self.key, AES.MODE_GCM)
        self.output_filename = output_filename
        self.input_filename = input_filename

    def read_file_in(self, file_in):
        self.salt = file_in.read(self.SALT_LENGTH)  # The salt we generated was 32 bits long
        nonce = file_in.read(self.NONCE_LENGTH)
        self.cipher = AES.new(self.key, AES.MODE_GCM, nonce=nonce)


class Encryptor(EncryptorBase):

    def write_header(self, file_out):
        file_out.write(self.salt)
        file_out.write(self.cipher.nonce)

    def write_body(self, file_in, file_out):
        while len(data := file_in.read(self.BUFFER_SIZE)):
            encrypted_data = self.cipher.encrypt(data)
            file_out.write(encrypted_data)

    def write_footer(self, file_out):
        tag = self.cipher.digest()
        assert len(tag) == self.TAG_LENGTH
        file_out.write(tag)

    def do_encryption(self):
        with open(self.output_filename, 'wb') as file_out, \
                open(self.input_filename, 'rb') as file_in:
            self.write_header(file_out)
            self.write_body(file_in, file_out)
            self.write_footer(file_out)


class Dcryptor(EncryptorBase):

    def __init__(self):
        super(Dcryptor, self).__init__()
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
        with open(self.output_filename, 'wb') as file_out, \
                open(self.input_filename, 'rb') as file_in:
            self.read_file_in(file_in)
            self.read_and_output(file_in, file_out)
            self.verify(file_in)


def RangeAndRemainder(whole, chunk):
    # yields equal chunks, then finishes with the remainder
    quotent, remainder = divmod(whole, chunk)
    for _ in range(quotent):
        yield chunk
    yield remainder


# e = Encryptor(input_filename='requirements.txt', output_filename='t2.txt.encrypted')
# de.do_decryption()

if __name__ == '__main__':
    import timeit

    s = """
de = Encryptor(input_filename='t2.txt', output_filename='t2.txt.encrypted')
de.do_encryption()
"""
    ds = """
de = Dcryptor(input_filename='t2.txt.encrypted', output_filename='t2.txt')
de.do_decryption()
"""

    print(timeit.timeit(stmt=s, number=1000, setup="from __main__ import Encryptor"))
    print(timeit.timeit(stmt=ds, number=1000, setup="from __main__ import Dcryptor"))
# 0.28165610500000005
# 0.4115074540000001
