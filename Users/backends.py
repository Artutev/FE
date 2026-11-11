"""Вход по имени пользователя без учёта регистра и пробелов по краям."""
from django.contrib.auth.backends import ModelBackend

from Users.models import User


def find_users(username):
    """Аккаунты с этим именем: сначала точное совпадение, потом без учёта регистра.

    Старые аккаунты могут отличаться только регистром («Anna» и «anna») — тогда вернётся
    несколько, и пароль решит, кто входит.
    """
    username = (username or '').strip()
    if not username:
        return []
    users = list(User.objects.filter(username__iexact=username).order_by('id'))
    users.sort(key=lambda user: user.username != username)  # точное совпадение — первым
    return users


class CaseInsensitiveModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        if username is None or password is None:
            return None
        candidates = find_users(username)
        if not candidates:
            User().set_password(password)  # то же время ответа, что и для существующего имени
            return None
        for user in candidates:
            if user.check_password(password) and self.user_can_authenticate(user):
                return user
        return None
