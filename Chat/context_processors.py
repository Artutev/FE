from Chat.services import total_unread


def chat_unread(request):
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {}
    return {'chat_unread': total_unread(user)}
