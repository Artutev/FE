from django.db import models

from django.contrib.auth.models import AbstractUser
from django.db.models import Q

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
    email_confirmation_code_hash = models.CharField(max_length=128, blank=True)
    is_profile_private = models.BooleanField('Закрытый профиль', default=False)


class FriendRequest(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Ожидает ответа'),
        ('accepted', 'Принята'),
        ('declined', 'Отклонена'),
    )

    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_friend_requests')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_friend_requests')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('from_user', 'to_user'), name='unique_friend_request_direction'),
        ]
        ordering = ('-created_at',)

    def __str__(self):
        return f'{self.from_user} -> {self.to_user} ({self.status})'