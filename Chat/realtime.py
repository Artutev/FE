"""Рассылка событий чата через channel layer (используется и из WebSocket, и из обычных HTTP-запросов)."""
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from Chat import services


def chat_group(conversation_id):
    return f'chat_{conversation_id}'


def user_group(user_id):
    return f'user_{user_id}'


def unread_payloads(conversation, exclude_user_id=None):
    """Для каждого участника: его общее число непрочитанных (для значка в шапке)."""
    payloads = []
    for membership in conversation.memberships.select_related('user'):
        if membership.user_id == exclude_user_id:
            continue
        payloads.append((membership.user_id, {
            'type': 'notify.unread',
            'total': services.total_unread(membership.user),
            'conversation_id': conversation.id,
        }))
    return payloads


def broadcast_message_sync(conversation, message, client_id=None):
    """Из синхронного кода (HTTP-представления): разослать новое сообщение и обновить значки."""
    layer = get_channel_layer()
    if layer is None:
        return
    async_to_sync(layer.group_send)(chat_group(conversation.id), {
        'type': 'chat.message',
        'message': services.serialize_message(message),
        'client_id': client_id,
    })
    for user_id, payload in unread_payloads(conversation, exclude_user_id=message.author_id):
        async_to_sync(layer.group_send)(user_group(user_id), payload)
