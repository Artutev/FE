"""Отправка писем EventTown.

Каждое письмо — пара шаблонов в templates/emails/: <name>.html (HTML-версия, наследует
emails/base.html) и <name>.txt (текстовая версия). Тема передаётся парой ru/en и
переводится через Users.i18n, как и строки в шаблонах ({% lang %}).
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, get_connection
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import translation

from Users.i18n import normalize_language, tr

logger = logging.getLogger(__name__)


def site_url():
    return getattr(settings, 'SITE_URL', '').rstrip('/') or 'http://127.0.0.1:8000'


def absolute_url(path):
    if path.startswith('http://') or path.startswith('https://'):
        return path
    return f'{site_url()}{path}'


def user_language(user, fallback='ru'):
    return normalize_language(getattr(user, 'language', '') or fallback)


def build_message(*, to, template, subject, context=None, language='ru'):
    """Собирает письмо (HTML + текст), но не отправляет."""
    language = normalize_language(language)
    ctx = {
        'LANGUAGE_CODE': language,
        'site_url': site_url(),
        'settings_url': absolute_url(reverse('Users:profile')),
        **(context or {}),
    }
    if isinstance(subject, (tuple, list)):
        # ('ru', 'en') или ('ru prefix', 'en prefix', 'суффикс без перевода, например название события')
        subject_text = tr(language, subject[0], subject[1]) + (subject[2] if len(subject) > 2 else '')
    else:
        subject_text = subject
    ctx['subject'] = subject_text
    with translation.override(language):
        text_body = render_to_string(f'emails/{template}.txt', ctx)
        html_body = render_to_string(f'emails/{template}.html', ctx)
    message = EmailMultiAlternatives(
        subject=f'{subject_text}',
        body=text_body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[to] if isinstance(to, str) else list(to),
    )
    message.attach_alternative(html_body, 'text/html')
    return message


def send_email(*, to, template, subject, context=None, language='ru', fail_silently=False):
    """Отправляет одно письмо. Возвращает True при успехе."""
    message = build_message(to=to, template=template, subject=subject, context=context, language=language)
    try:
        return message.send(fail_silently=False) > 0
    except Exception:  # SMTP/сеть: не роняем запрос пользователя
        logger.exception('Email "%s" to %s failed', template, message.to)
        if not fail_silently:
            raise
        return False


def send_bulk(messages):
    """Отправляет пачку писем через одно SMTP-соединение. Возвращает число отправленных."""
    messages = [m for m in messages if m is not None]
    if not messages:
        return 0
    try:
        with get_connection() as connection:
            return connection.send_messages(messages) or 0
    except Exception:
        logger.exception('Bulk email (%s messages) failed', len(messages))
        return 0
