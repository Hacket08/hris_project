from cryptography.fernet import Fernet

from app.core.config import get_settings

settings = get_settings()
_fernet = Fernet(settings.field_encryption_key.encode("utf-8"))


def encrypt_field(plaintext: str) -> str:
    return _fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_field(ciphertext: str) -> str:
    return _fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
