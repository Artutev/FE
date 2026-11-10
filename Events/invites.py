"""Приглашения друзей на мероприятие: кого можно позвать и отправка приглашения в личный чат."""
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.urls import reverse

from Chat import services as chat
from Chat.realtime import broadcast_message_sync
from Events.models import EventInvite, EventRegistration
from Users.i18n import tr
from Users.models import FriendRequest, User
from Users.templatetags.language_tags import MONTH_LABELS


def friends_of(user):
    pairs = FriendRequest.objects.filter(
        Q(from_user=user) | Q(to_user=user), status='accepted',
    ).values_list('from_user_id', 'to_user_id')
    ids = {uid for pair in pairs for uid in pair if uid != user.pk}
    return User.objects.filter(pk__in=ids, is_active=True).order_by('username')


def can_invite(user, event, has_access):
    """Звать может любой, кто сам видит событие (для приватного — создатель или по ссылке), пока оно не прошло."""
    return user.is_authenticated and has_access and not event.has_passed


def invite_candidates(user, event):
    """Друзья со статусом: 'going' — уже записан, 'invited' — уже приглашён, '' — можно позвать."""
    friends = list(friends_of(user))
    ids = [f.pk for f in friends]
    going = set(EventRegistration.objects.filter(event=event, user_id__in=ids).values_list('user_id', flat=True))
    invited = set(EventInvite.objects.filter(event=event, invitee_id__in=ids).values_list('invitee_id', flat=True))
    for friend in friends:
        friend.invite_status = 'going' if friend.pk in going else 'invited' if friend.pk in invited else ''
    return friends


def event_link(event, request):
    """Ссылка для приглашения: на оформленное пригласительное, если оно есть, иначе на страницу события."""
    from Events.models import InvitationCard
    card = InvitationCard.objects.filter(event=event).only('code').first()
    if card:
        return request.build_absolute_uri(reverse('invite_card', args=[card.code]))
    path = reverse('Events:event_detail', args=[event.id])
    if event.is_private and event.access_token:
        path += f'?token={event.access_token}'
    return request.build_absolute_uri(path)


def _when(event, language):
    if not event.date:
        return ''
    months = MONTH_LABELS.get(language, MONTH_LABELS['ru'])
    text = f'{event.date.day} {months[event.date.month]}'
    if event.time:
        text += f', {event.time.strftime("%H:%M")}'
    return text


def invitation_text(event, link, language):
    when = _when(event, language)
    head = tr(language, 'Приглашаю тебя на', "You're invited to")
    return f'{head} «{event.name}»' + (f' — {when}' if when else '') + f'\n{link}'


def send_invites(inviter, event, invitee_ids, request, language):
    """Создаёт приглашения и пишет каждому другу в личный чат. Возвращает число отправленных."""
    allowed = {f.pk: f for f in invite_candidates(inviter, event) if not f.invite_status}
    link = event_link(event, request)
    text = invitation_text(event, link, language)
    sent = 0
    for invitee_id in invitee_ids:
        friend = allowed.get(invitee_id)
        if friend is None:
            continue
        try:
            with transaction.atomic():
                EventInvite.objects.create(event=event, inviter=inviter, invitee=friend)
        except IntegrityError:  # уже позвал кто-то другой
            continue
        conversation = chat.get_or_create_direct(inviter, friend)
        message = chat.create_message(conversation, inviter, text)
        if message is not None:
            broadcast_message_sync(conversation, message)
        sent += 1
    return sent
