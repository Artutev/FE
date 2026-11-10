"""Шифрование текста сообщений в базе (Fernet: AES-128-CBC + HMAC-SHA256).

Ключи берутся из CHAT_ENCRYPTION_KEYS (через запятую, первый — для новых записей,
остальные — только для чтения, чтобы можно было сменить ключ без потери старых
сообщений). Если ключей нет, ключ выводится из SECRET_KEY — годится для разработки
и тестов, на проде задайте отдельный ключ и храните его копию вне сервера.
"""
import base64
import hashlib
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from django.conf import settings

PREFIX = 'fernet:'


@lru_cache(maxsize=None)
def _cipher(keys):
    return MultiFernet([Fernet(key) for key in keys])


def _keys():
    keys = tuple(k.strip() for k in getattr(settings, 'CHAT_ENCRYPTION_KEYS', []) if k.strip())
    if keys:
        return keys
    digest = hashlib.sha256(f'chat-encryption:{settings.SECRET_KEY}'.encode()).digest()
    return (base64.urlsafe_b64encode(digest).decode(),)


def encrypt(text):
    # Шифруем всегда, даже если пользователь сам написал текст, начинающийся с PREFIX:
    # в Python значение поля — всегда открытый текст, шифротекст живёт только в базе.
    if text is None or text == '':
        return text
    token = _cipher(_keys()).encrypt(str(text).encode('utf-8'))
    return PREFIX + token.decode('ascii')


def decrypt(value):
    """Расшифровать; старые незашифрованные значения возвращаются как есть."""
    if not value or not value.startswith(PREFIX):
        return value
    try:
        return _cipher(_keys()).decrypt(value[len(PREFIX):].encode('ascii')).decode('utf-8')
    except InvalidToken:
        # Неверный ключ — не роняем страницу, но и текст не показываем
        return '🔒'


def is_encrypted(value):
    return bool(value) and value.startswith(PREFIX)
