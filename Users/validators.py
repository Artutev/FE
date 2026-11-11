from django.core.exceptions import ValidationError

# Латинские буквы, цифры и обычные символы клавиатуры (ASCII 33–126), без пробелов.
PASSWORD_ALLOWED = {chr(code) for code in range(33, 127)}
PASSWORD_CHARS_MESSAGE = 'Пароль может содержать только латинские буквы, цифры и символы, без пробелов.'


class LatinPasswordValidator:
    def validate(self, password, user=None):
        if any(char not in PASSWORD_ALLOWED for char in password):
            raise ValidationError(PASSWORD_CHARS_MESSAGE, code='password_invalid_chars')

    def get_help_text(self):
        return PASSWORD_CHARS_MESSAGE
