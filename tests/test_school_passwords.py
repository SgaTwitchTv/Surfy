import dataclasses
import unittest
from greenwave.school_accounts.config import Config
from greenwave.school_accounts.crypto import Passwords,password,token_hash
from greenwave.school_accounts.errors import AuthError
PASS='Valid password 123!'

class CryptoConfigTests(unittest.TestCase):
    def test_password_unicode_confirmation_and_no_trim(self):
        for value in ['short','x'*129,'😀'*129,None,'\ud800'*12]:
            with self.assertRaises(AuthError):password(value)
        password('😀'*128)
        with self.assertRaises(AuthError):password(PASS,None)
        kdf=Passwords(n=1024);encoded=kdf.hash(' '+PASS+' ')
        self.assertTrue(kdf.verify(' '+PASS+' ',encoded)[0]);self.assertFalse(kdf.verify(PASS,encoded)[0])
        self.assertFalse(kdf.verify(PASS,'scrypt$v1$999999999$8$1$32$'+'a'*32+'$'+'b'*64)[0])
        self.assertFalse(kdf.verify(PASS,'malformed')[0]);self.assertFalse(kdf.verify(None,encoded)[0])
        with self.assertRaises(AuthError):token_hash('raw-invalid')
        kdf.slots.acquire();kdf.slots.acquire()
        try:
            with self.assertRaises(AuthError):kdf.hash(PASS)
        finally:kdf.slots.release();kdf.slots.release()

    def test_real_scrypt_configuration_hash_verify_legacy_rehash(self):
        kdf=Passwords();encoded=kdf.hash(PASS)
        self.assertIn('$131072$8$1$32$',encoded)
        self.assertEqual(kdf.verify(PASS,encoded),(True,False))
        old=Passwords(n=65536).hash(PASS)
        self.assertEqual(kdf.verify(PASS,old),(True,True))

    def test_real_profile_requires_https_secure_and_tls_mail(self):
        cfg=Config('http://127.0.0.1:8770',('127.0.0.1:8770',),b'a'*32,b'b'*32)
        cfg.validate()
        for changes in [{'profile':'real'},{'bind':'0.0.0.0'},{'smtp_host':'smtp.example.org'},{'hosts':('*',)},{'csrf_key':b'x'},{'base_url':'http://127.0.0.1:8770/path'}]:
            with self.assertRaises(ValueError):dataclasses.replace(cfg,**changes).validate()
        real=dataclasses.replace(cfg,profile='real',base_url='https://school.example.test',hosts=('school.example.test',),smtp_host='smtp.example.test',smtp_mode='starttls',trusted_proxy='127.0.0.1')
        self.assertTrue(real.validate().secure)
