from django.db import models

from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    THEME_CHOICES = (
        ('light', 'Светлая тема'),
        ('dark', 'Темная тема'),
        ('auto', 'Автоматично'),
    )
    
    # image = models.ImageField(upload_to="users_images", null=True, blank=True)
    birthDate = models.DateField(null=True, blank=True)
    theme_preference = models.CharField(
        max_length=10,
        choices=THEME_CHOICES,
        default='auto',
        verbose_name='Предпочитаемая тема'
    )