from django.utils import translation

from Users.i18n import get_language


class SessionLanguageMiddleware:
    """Включает язык из сессии, чтобы встроенные сообщения Django (ошибки форм,
    валидаторы паролей) тоже выводились на выбранном языке."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        language = get_language(request)
        translation.activate(language)
        request.LANGUAGE_CODE = language
        response = self.get_response(request)
        response.headers.setdefault('Content-Language', language)
        translation.deactivate()
        return response
