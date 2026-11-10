import secrets
from datetime import date

from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class EventType(models.Model):
    code = models.SlugField('Код', max_length=50, unique=True)
    name_ru = models.CharField('Название на русском', max_length=100)
    name_en = models.CharField('Название на английском', max_length=100)
    is_active = models.BooleanField('Активен', default=True)
    sort_order = models.PositiveIntegerField('Порядок', default=0)

    class Meta:
        ordering = ('sort_order', 'name_ru')
        verbose_name = 'Тип мероприятия'
        verbose_name_plural = 'Типы мероприятий'

    def __str__(self):
        return self.name_ru

    def localized_name(self, language='ru'):
        from Users.i18n import tr
        if language != 'en' and language != 'ru':
            builtin = Event.EVENT_TYPE_LABELS.get(language, {}).get(self.code)
            if builtin:
                return builtin
        return tr(language, self.name_ru, self.name_en)

    @classmethod
    def localized_choices(cls, language='ru'):
        return [
            (event_type.code, event_type.localized_name(language))
            for event_type in cls.objects.filter(is_active=True)
        ]

    @classmethod
    def label_for(cls, code, language='ru'):
        event_type = cls.objects.filter(code=code).first()
        if event_type:
            return event_type.localized_name(language)
        labels = Event.EVENT_TYPE_LABELS.get(language, Event.EVENT_TYPE_LABELS['ru'])
        return labels.get(code, code)


class Event(models.Model):
    EVENT_TYPE_LABELS = {
        'ru': {
            'concert': 'Концерт',
            'theater': 'Театр',
            'cinema': 'Кино',
            'exhibition': 'Выставка',
            'lecture': 'Лекция',
            'wedding': 'Свадьба',
            'other': 'Другое',
        },
        'en': {
            'concert': 'Concert',
            'theater': 'Theater',
            'cinema': 'Cinema',
            'exhibition': 'Exhibition',
            'lecture': 'Lecture',
            'wedding': 'Wedding',
            'other': 'Other',
        },
        'cs': {
            'concert': 'Koncert',
            'theater': 'Divadlo',
            'cinema': 'Kino',
            'exhibition': 'Výstava',
            'lecture': 'Přednáška',
            'wedding': 'Svatba',
            'other': 'Ostatní',
        },
    }

    EVENT_TYPE_CHOICES = [
        (code, label)
        for code, label in EVENT_TYPE_LABELS['ru'].items()
    ]

    name = models.CharField("Название", max_length=200)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    location = models.CharField("Место проведения", max_length=200, blank=True)
    description = models.TextField("Описание", blank=True)
    latitude = models.FloatField("Широта", null=True, blank=True)
    longitude = models.FloatField("Долгота", null=True, blank=True)
    event_type = models.CharField("Тип мероприятия", max_length=50, choices=EVENT_TYPE_CHOICES, default='other')
    is_private = models.BooleanField("Приватное мероприятие", default=False)
    access_token = models.CharField("Ключ доступа", max_length=64, blank=True, null=True, unique=True)
    bride_name = models.CharField("Имя невесты", max_length=100, blank=True, null=True)
    groom_name = models.CharField("Имя жениха", max_length=100, blank=True, null=True)
    wedding_theme = models.CharField("Тема свадьбы", max_length=150, blank=True, null=True)
    guest_count = models.PositiveIntegerField("Ожидаемое количество гостей", blank=True, null=True)
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='events',
        null=True, blank=True
    )

    is_past = models.BooleanField("Прошедшее", default=False)
    reminder_sent = models.BooleanField("Напоминание отправлено", default=False)
    cover = models.ImageField("Обложка", upload_to='covers/', blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if self.is_private and not self.access_token:
            self.access_token = self._generate_unique_token()
        if not self.is_private:
            self.access_token = None
        super().save(*args, **kwargs)

    def _generate_unique_token(self):
        token = secrets.token_urlsafe(24)
        while Event.objects.filter(access_token=token).exists():
            token = secrets.token_urlsafe(24)
        return token

    @property
    def has_passed(self):
        return bool(self.date) and self.date < date.today()

    def __str__(self):
        return f"{self.name} ({self.date})"


class EventRegistration(models.Model):
    """Модель для регистрации пользователя на событие."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='event_registrations')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='registrations')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'event')
        verbose_name = "Регистрация на событие"
        verbose_name_plural = "Регистрации на события"

    def __str__(self):
        return f"{self.user.username} → {self.event.name}"
