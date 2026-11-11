"""Незавершённые регистрации: аккаунт создан, но почта так и не подтверждена.

Такой аккаунт не должен навсегда занимать имя и email: человек мог ошибиться в адресе или не получить письмо.
Пересоздать его можно:
- сразу, если регистрируются на тот же email (это тот же человек, просто пробует ещё раз);
- с другим email — только когда код уже истёк, чтобы нельзя было «перехватить» чужую регистрацию,
  пока человек вводит код.
"""
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from Users.models import User

CONFIRM_CODE_TTL_MINUTES = 30


def _pending():
    return User.objects.filter(is_active=False, last_login__isnull=True)


def replaceable_signups(username='', email=''):
    """Незавершённые регистрации с этим именем или email, которые можно удалить и создать заново."""
    match = Q()
    if username:
        match |= Q(username__iexact=username)
    if email:
        match |= Q(email__iexact=email)
    if not match:
        return User.objects.none()
    expired = timezone.now() - timedelta(minutes=CONFIRM_CODE_TTL_MINUTES)
    reusable = Q(email_confirmation_sent_at__isnull=True) | Q(email_confirmation_sent_at__lt=expired)
    if email:
        reusable |= Q(email__iexact=email)
    return _pending().filter(match).filter(reusable)


def taken(field, value, email=''):
    """Занято ли имя/email кем-то, кроме регистраций, которые можно пересоздать."""
    others = User.objects.filter(**{f'{field}__iexact': value})
    replaceable = replaceable_signups(**{field: value, 'email': email} if field == 'username' else {'email': value})
    return others.exclude(pk__in=replaceable.values('pk')).exists()
