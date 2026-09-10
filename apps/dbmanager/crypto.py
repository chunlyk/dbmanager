"""密码加解密与随机密码生成工具。"""
import base64
import hashlib
import secrets
import string

from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings

_SYMBOLS = "!@#$%^&*()-_=+"


def _fernet() -> Fernet:
    """由配置密钥派生出 32 字节 Fernet key。"""
    digest = hashlib.sha256(settings.PASSWORD_ENCRYPTION_KEY.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_password(plain: str) -> str:
    """明文 -> 密文（Fernet / AES-128-CBC + HMAC）。"""
    if not plain:
        return ""
    return _fernet().encrypt(plain.encode("utf-8")).decode("ascii")


def decrypt_password(token: str) -> str:
    """密文 -> 明文。"""
    if not token:
        return ""
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError):
        # 密钥更换或数据损坏，返回空串而不是抛异常打断流程
        return ""


def generate_password(length: int | None = None) -> str:
    """生成满足复杂度要求的随机密码。"""
    length = length or getattr(settings, "PASSWORD_LENGTH", 20)
    length = max(length, 12)
    alphabet = string.ascii_letters + string.digits + _SYMBOLS

    while True:
        pwd = "".join(secrets.choice(alphabet) for _ in range(length))
        if (
            any(c.islower() for c in pwd)
            and any(c.isupper() for c in pwd)
            and any(c.isdigit() for c in pwd)
            and any(c in _SYMBOLS for c in pwd)
        ):
            return pwd