"""Отправка писем через Gmail API (HTTPS) вместо SMTP.

Нужен, когда SMTP-вход в Gmail с сервера заблокирован (облачные IP).
Авторизация — OAuth 2.0 с refresh token для scope gmail.send:
    GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN
Получить refresh token: `python manage.py gmail_authorize` (см. docs/DEPLOY.md).
"""
import base64
import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)

TOKEN_URL = 'https://oauth2.googleapis.com/token'
SEND_URL = 'https://gmail.googleapis.com/gmail/v1/users/me/messages/send'
SCOPE = 'https://www.googleapis.com/auth/gmail.send'

_token_lock = threading.Lock()
_token_cache = {'value': None, 'expires_at': 0.0}


class GmailAPIError(Exception):
    pass


def _post(url, data, headers, timeout):
    request = urllib.request.Request(url, data=data, headers=headers, method='POST')
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode('utf-8') or '{}')
    except urllib.error.HTTPError as exc:
        body = exc.read().decode('utf-8', errors='replace')[:500]
        raise GmailAPIError(f'HTTP {exc.code}: {body}') from exc


def get_access_token(force_refresh=False):
    """Access token живёт ~1 час; кэшируем на процесс и обновляем заранее."""
    with _token_lock:
        if not force_refresh and _token_cache['value'] and time.time() < _token_cache['expires_at'] - 60:
            return _token_cache['value']
        payload = urllib.parse.urlencode({
            'client_id': settings.GMAIL_CLIENT_ID,
            'client_secret': settings.GMAIL_CLIENT_SECRET,
            'refresh_token': settings.GMAIL_REFRESH_TOKEN,
            'grant_type': 'refresh_token',
        }).encode()
        data = _post(
            TOKEN_URL, payload, {'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=getattr(settings, 'EMAIL_TIMEOUT', 15) or 15,
        )
        token = data.get('access_token')
        if not token:
            raise GmailAPIError(f'No access_token in response: {list(data)}')
        _token_cache['value'] = token
        _token_cache['expires_at'] = time.time() + int(data.get('expires_in', 3600))
        return token


class GmailAPIBackend(BaseEmailBackend):
    def send_messages(self, email_messages):
        if not email_messages:
            return 0
        sent = 0
        for message in email_messages:
            try:
                self._send(message)
                sent += 1
            except Exception:
                logger.exception('Gmail API send failed (to=%s)', message.to)
                if not self.fail_silently:
                    raise
        return sent

    def _send(self, message):
        raw = base64.urlsafe_b64encode(message.message().as_bytes()).decode('ascii')
        body = json.dumps({'raw': raw}).encode()
        timeout = getattr(settings, 'EMAIL_TIMEOUT', 15) or 15
        for attempt in (1, 2):
            headers = {
                'Authorization': f'Bearer {get_access_token(force_refresh=attempt == 2)}',
                'Content-Type': 'application/json',
            }
            try:
                return _post(SEND_URL, body, headers, timeout=timeout)
            except GmailAPIError as exc:
                # 401 — токен протух раньше срока: обновляем и пробуем ещё раз
                if attempt == 1 and str(exc).startswith('HTTP 401'):
                    continue
                raise
