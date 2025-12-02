from django.db import models
from django.contrib.auth import get_user_model


User = get_user_model()


class Event(models.Model):
    event_types = [
        ('concert', 'Концерт'),
        ('theater', 'Театр'),
        ('cinema', 'Кино'),
        ('exhibition', 'Выставка'),
        ('lecture', 'Лекция'),
        ('other', 'Другое'),
    ]
    name = models.CharField("Название", max_length=200)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    location = models.CharField("Место проведения", max_length=200)
    description = models.TextField("Описание")
    event_type = models.CharField("Тип мероприятия", max_length=50, choices=event_types, default='other')
    creator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='events',
        null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.date})"
