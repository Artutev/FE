from django.contrib import messages as flash
from django.contrib.auth.decorators import login_required
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from Chat import services
from Chat.models import Conversation, Message
from Chat.realtime import broadcast_message_sync
from Events.models import Event
from Users.i18n import get_language, tr
from Users.models import User

PAGE_SIZE = 50


def _get_readable(request, conversation_id):
    conversation = get_object_or_404(Conversation.objects.select_related('event'), pk=conversation_id)
    if not services.can_read(request.user, conversation):
        raise Http404()
    services.ensure_member(conversation, request.user)
    return conversation


def _friends(user):
    from django.db.models import Q
    return User.objects.filter(
        Q(sent_friend_requests__to_user=user, sent_friend_requests__status='accepted')
        | Q(received_friend_requests__from_user=user, received_friend_requests__status='accepted'),
        is_active=True,
    ).distinct().order_by('username')


@login_required(login_url='Users:login')
def chat_list(request):
    conversations = services.conversations_for(request.user)
    with_chat = {c.peer.pk for c in conversations if getattr(c, 'peer', None)}
    return render(request, 'Chat/list.html', {
        'conversations': conversations,
        'friends_without_chat': [f for f in _friends(request.user) if f.pk not in with_chat],
    })


@login_required(login_url='Users:login')
def chat_detail(request, conversation_id):
    conversation = _get_readable(request, conversation_id)
    recent = list(conversation.messages.select_related('author').order_by('-created_at', '-id')[:PAGE_SIZE])
    recent.reverse()
    services.mark_read(conversation, request.user)
    peer = services.other_member(conversation, request.user) if conversation.kind == Conversation.DIRECT else None
    return render(request, 'Chat/detail.html', {
        'conversation': conversation,
        'peer': peer,
        'chat_messages_json': [services.serialize_message(m) for m in recent],
        'chat_reads_json': services.read_marks(conversation),
        'has_more': conversation.messages.count() > len(recent),
        'can_write': services.can_write(request.user, conversation),
        'member_count': conversation.memberships.count(),
        'max_length': Message.MAX_LENGTH,
    })


@login_required(login_url='Users:login')
@require_POST
def start_direct(request, username):
    language = get_language(request)
    other = get_object_or_404(User, username=username, is_active=True)
    if other == request.user or not services.are_friends(request.user, other):
        flash.error(request, tr(language, 'Писать можно только друзьям.', 'You can only message friends.'))
        return redirect('Users:friends')
    conversation = services.get_or_create_direct(request.user, other)
    return redirect('Chat:detail', conversation_id=conversation.pk)


@login_required(login_url='Users:login')
def event_chat(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    if not services.can_join_event_chat(request.user, event):
        flash.error(request, tr(
            get_language(request),
            'Чат доступен участникам мероприятия. Сначала зарегистрируйтесь.',
            'The chat is for people attending. Register first.',
        ))
        return redirect('Events:event_detail', event_id=event.pk)
    conversation = services.get_or_create_event_chat(event)
    services.ensure_member(conversation, request.user)
    return redirect('Chat:detail', conversation_id=conversation.pk)


@login_required(login_url='Users:login')
def older_messages(request, conversation_id):
    """История для подгрузки при прокрутке вверх: ?before=<id сообщения>."""
    conversation = _get_readable(request, conversation_id)
    qs = conversation.messages.select_related('author').order_by('-created_at', '-id')
    before = request.GET.get('before')
    if before and before.isdigit():
        qs = qs.filter(id__lt=int(before))
    batch = list(qs[:PAGE_SIZE + 1])
    has_more = len(batch) > PAGE_SIZE
    batch = batch[:PAGE_SIZE]
    batch.reverse()
    return JsonResponse({'messages': [services.serialize_message(m) for m in batch], 'has_more': has_more})


@login_required(login_url='Users:login')
@require_POST
def send_message(request, conversation_id):
    """Запасной путь, если WebSocket недоступен (и для будущего мобильного приложения)."""
    conversation = _get_readable(request, conversation_id)
    if not services.can_write(request.user, conversation):
        return JsonResponse({'error': 'forbidden'}, status=403)
    message = services.create_message(conversation, request.user, request.POST.get('text', ''))
    if message is None:
        return JsonResponse({'error': 'empty'}, status=400)
    broadcast_message_sync(conversation, message, client_id=request.POST.get('client_id'))
    return JsonResponse({'message': services.serialize_message(message)})
