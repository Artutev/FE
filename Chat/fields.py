from django.db import models

from Chat import crypto


class EncryptedTextField(models.TextField):
    """TextField, который хранит значение в базе в зашифрованном виде.

    Поиск и фильтрация по содержимому в базе невозможны (там шифротекст).
    """

    def from_db_value(self, value, expression, connection):
        return crypto.decrypt(value)

    # to_python не трогаем: TextField.get_prep_value вызывает его перед записью,
    # а в Python значение — всегда открытый текст. Расшифровка только при чтении из базы.

    def get_prep_value(self, value):
        value = super().get_prep_value(value)
        return crypto.encrypt(value)
