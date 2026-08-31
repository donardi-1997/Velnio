from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import hashlib

def _get_key() -> bytes:
    key = hashlib.sha256(settings.ENCRYPTION_KEY.encode()).digest()
    return base64.urlsafe_b64encode(key)

_fernet = Fernet(_get_key())

def encrypt_value(value: str) -> str:
    return _fernet.encrypt(value.encode()).decode()

def decrypt_value(encrypted: str) -> str:
    return _fernet.decrypt(encrypted.encode()).decode()
