"""Логика чата: кто с кем может переписываться, создание чатов, непрочитанные."""
from django.db import IntegrityError, transaction
from django.db.models import Count, F, OuterRef, Q, Subquery
from django.utils import timezone

from Chat.models import Conversation, Membership, Message
from Events.models import EventRegistration
from Users.models import FriendRequest


def are_friends(user_a, user_b):
    return FriendRequest.objects.filter(
        Q(from_user=user_a, to_user=user_b) | Q(from_user=user_b, to_user=user_a),
        status='accepted',
    ).exists()


def direct_key(user_a, user_b):
    low, high = sorted((user_a.pk, user_b.pk))
    return f'{low}:{high}'


def get_or_create_direct(user_a, user_b):
    key = direct_key(user_a, user_b)
    conversation = Conversation.objects.filter(direct_key=key).first()
    if conversation is None:
        try:
            with transaction.atomic():
                conversation = Conversation.objects.create(kind=Conversation.DIRECT, direct_key=key)
                Membership.objects.bulk_create([
                    Membership(conversation=conversation, user=user_a),
                    Membership(conversation=conversation, user=user_b),
                ])
        except IntegrityError:  # гонка: чат создал второй участник одновременно
            conversation = Conversation.objects.get(direct_key=key)
    return conversation


def can_join_event_chat(user, event):
    if not user.is_authenticated:
        return False
    if event.creator_id == user.pk:
        return True
    return EventRegistration.objects.filter(user=user, event=event).exists()


def get_or_create_event_chat(event):
    conversation, _ = Conversation.objects.get_or_create(event=event, defaults={'kind': Conversation.EVENT})
    return conversation


def ensure_member(conversation, user):
    Membership.objects.get_or_create(conversation=conversation, user=user)


def can_read(user, conversation):
    if not user.is_authenticated:
        return False
    if conversation.kind == Conversation.EVENT:
        return can_join_event_chat(user, conversation.event)
    return Membership.objects.filter(conversation=conversation, user=user).exists()


def can_write(user, conversation):
    """Писать в личный чат можно только пока вы друзья; в чат события — пока вы участник."""
    if not can_read(user, conversation):
        return False
    if conversation.kind == Conversation.DIRECT:
        other = other_member(conversation, user)
        return other is not None and other.is_active and are_friends(user, other)
    return True


def other_member(conversation, user):
    membership = conversation.memberships.select_related('user').exclude(user=user).first()
    return membership.user if membership else None


def create_message(conversation, author, text):
    text = (text or '').strip()[:Message.MAX_LENGTH]
    if not text:
        return None
    message = Message.objects.create(conversation=conversation, author=author, text=text)
    Conversation.objects.filter(pk=conversation.pk).update(last_message_at=message.created_at)
    Membership.objects.filter(conversation=conversation, user=author).update(last_read_at=message.created_at)
    return message


def mark_read(conversation, user):
    """Отметить чат прочитанным; возвращает время отметки (его рассылаем остальным)."""
    now = timezone.now()
    Membership.objects.filter(conversation=conversation, user=user).update(last_read_at=now)
    return now


def read_marks(conversation):
    """{user_id: ISO-время} — до какого момента каждый участник дочитал чат (для галочек ✓✓)."""
    return {
        membership.user_id: membership.last_read_at.isoformat()
        for membership in conversation.memberships.exclude(last_read_at=None)
    }


def unread_count(conversation, user):
    membership = Membership.objects.filter(conversation=conversation, user=user).first()
    qs = conversation.messages.exclude(author=user)
    if membership and membership.last_read_at:
        qs = qs.filter(created_at__gt=membership.last_read_at)
    return qs.count()


def total_unread(user):
    """Сумма непрочитанных по всем чатам пользователя — для значка в шапке."""
    if not user.is_authenticated:
        return 0
    return Message.objects.filter(
        conversation__memberships__user=user,
    ).exclude(author=user).filter(
        Q(conversation__memberships__last_read_at__isnull=True)
        | Q(created_at__gt=F('conversation__memberships__last_read_at'))
    ).count()


def conversations_for(user):
    """Чаты пользователя (новые сверху) с последним сообщением и числом непрочитанных."""
    last_message = Message.objects.filter(conversation=OuterRef('pk')).order_by('-created_at', '-id')
    conversations = (
        Conversation.objects.filter(memberships__user=user)
        .select_related('event')
        .annotate(
            last_text=Subquery(last_message.values('text')[:1]),
            last_author_id=Subquery(last_message.values('author_id')[:1]),
            unread=Count(
                'messages',
                filter=~Q(messages__author=user) & (
                    Q(memberships__user=user, memberships__last_read_at__isnull=True)
                    | Q(memberships__user=user, messages__created_at__gt=F('memberships__last_read_at'))
                ),
                distinct=True,
            ),
        )
        .order_by(F('last_message_at').desc(nulls_last=True), '-created_at')
    )
    result = []
    for conversation in conversations:
        if conversation.kind == Conversation.DIRECT:
            conversation.peer = other_member(conversation, user)
        result.append(conversation)
    return result


def serialize_message(message):
    author = message.author
    return {
        'id': message.id,
        'text': message.text,
        'created_at': message.created_at.isoformat(),
        'author': {
            'id': author.id if author else None,
            'username': author.username if author else '—',
            'avatar': author.avatar.url if author and author.avatar else '',
        },
    }
