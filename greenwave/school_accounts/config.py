import ipaddress
import json
import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit


@dataclass(frozen=True)
class Config:
    base_url: str
    hosts: tuple
    csrf_key: bytes
    rate_key: bytes
    profile: str='demo'
    bind: str='127.0.0.1'
    port: int=8770
    smtp_host: str='127.0.0.1'
    smtp_port: int=1025
    smtp_mode: str='plain'
    smtp_sender: str='greenwave@example.test'
    smtp_user: str=''
    smtp_password: str=''
    trusted_proxy: str=''
    tls_cert: str=''
    tls_key: str=''

    @property
    def secure(self):
        return self.profile=='real'

    @property
    def origin(self):
        parsed=urlsplit(self.base_url)
        return parsed.scheme+'://'+parsed.netloc

    def validate(self):
        parsed=urlsplit(self.base_url)
        if parsed.scheme not in {'http','https'} or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in {'','/'}:
            raise ValueError('Invalid PUBLIC_BASE_URL')
        if self.profile not in {'demo','real'} or len(self.csrf_key)<32 or len(self.rate_key)<32 or parsed.netloc not in self.hosts:
            raise ValueError('Invalid profile, secrets or exact Host allowlist')
        if any(not h or '/' in h or '*' in h or '@' in h for h in self.hosts):
            raise ValueError('Host allowlist must be exact')
        if self.smtp_mode not in {'plain','starttls','smtps'} or not 1<=self.smtp_port<=65535 or not 0<=self.port<=65535:
            raise ValueError('Invalid SMTP or HTTP port')
        if self.profile=='demo':
            if self.bind not in {'127.0.0.1','::1','localhost'} or parsed.hostname not in {'127.0.0.1','localhost','::1'} or self.smtp_host not in {'127.0.0.1','localhost','::1'} or not self.smtp_sender.endswith('@example.test'):
                raise ValueError('Demo is local-only with synthetic email addresses')
        else:
            if parsed.scheme!='https' or self.smtp_mode=='plain':
                raise ValueError('Real deployment requires HTTPS, Secure cookies and verified SMTP TLS')
            if not self.tls_cert and (not self.trusted_proxy or self.bind not in {'127.0.0.1','::1'}):
                raise ValueError('Use direct TLS or an explicitly trusted local HTTPS proxy')
        if bool(self.tls_cert)!=bool(self.tls_key) or bool(self.smtp_user)!=bool(self.smtp_password):
            raise ValueError('Incomplete TLS/SMTP credentials')
        if self.trusted_proxy:
            ipaddress.ip_address(self.trusted_proxy)
        from greenwave.school_data.validation import email
        email(self.smtp_sender)
        return self

    @classmethod
    def environment(cls,bind,port):
        keys=json.loads(Path(os.environ['SCHOOL_SECRET_FILE']).read_text(encoding='utf-8'))
        return cls(base_url=os.environ['SCHOOL_PUBLIC_BASE_URL'],hosts=tuple(os.environ['SCHOOL_ALLOWED_HOSTS'].split(',')),
                   csrf_key=bytes.fromhex(keys['csrf_key']),rate_key=bytes.fromhex(keys['rate_key']),
                   profile=os.environ['SCHOOL_PROFILE'],bind=bind,port=port,
                   smtp_host=os.getenv('SCHOOL_SMTP_HOST','127.0.0.1'),smtp_port=int(os.getenv('SCHOOL_SMTP_PORT','1025')),
                   smtp_mode=os.getenv('SCHOOL_SMTP_MODE','plain'),smtp_sender=os.getenv('SCHOOL_SMTP_SENDER','greenwave@example.test'),
                   smtp_user=os.getenv('SCHOOL_SMTP_USER',''),smtp_password=os.getenv('SCHOOL_SMTP_PASSWORD',''),
                   trusted_proxy=os.getenv('SCHOOL_TRUSTED_PROXY',''),tls_cert=os.getenv('SCHOOL_TLS_CERT',''),tls_key=os.getenv('SCHOOL_TLS_KEY','')).validate()
