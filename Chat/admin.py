from django.contrib import admin

from Chat.models import Conversation, Message


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ('id', 'kind', 'event', 'last_message_at')
    list_filter = ('kind',)


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'conversation', 'author', 'created_at')
    # текст зашифрован в базе — искать можно только по автору
    search_fields = ('author__username',)
