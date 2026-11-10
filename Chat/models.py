from django.conf import settings
from django.db import models

from Chat.fields import EncryptedTextField


class Conversation(models.Model):
    DIRECT = 'direct'
    EVENT = 'event'
    KIND_CHOICES = ((DIRECT, 'Личный'), (EVENT, 'Чат мероприятия'))

    kind = models.CharField('Тип', max_length=10, choices=KIND_CHOICES)
    # Для личного чата — "меньший_id:больший_id", чтобы между двумя людьми был ровно один чат
    direct_key = models.CharField(max_length=40, unique=True, null=True, blank=True)
    event = models.OneToOneField(
        'Events.Event', on_delete=models.CASCADE, null=True, blank=True, related_name='chat',
    )
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='Membership', related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        verbose_name = 'Чат'
        verbose_name_plural = 'Чаты'

    def __str__(self):
        if self.kind == self.EVENT and self.event_id:
            return f'Чат: {self.event}'
        return f'Личный чат #{self.pk}'


class Membership(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='memberships')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='chat_memberships')
    joined_at = models.DateTimeField(auto_now_add=True)
    last_read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=('conversation', 'user'), name='unique_chat_membership'),
        ]


class Message(models.Model):
    MAX_LENGTH = 2000

    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='chat_messages',
    )
    # В базе хранится зашифрованным (Chat/crypto.py)
    text = EncryptedTextField('Текст', max_length=MAX_LENGTH)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ('created_at', 'id')
        indexes = [models.Index(fields=('conversation', 'created_at'))]
        verbose_name = 'Сообщение'
        verbose_name_plural = 'Сообщения'

    def __str__(self):
        return f'{self.author}: {self.text[:40]}'
