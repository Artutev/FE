"""Письма участникам мероприятий: запись, изменения, отмена, напоминание."""
from django.urls import reverse

from Users.emails import absolute_url, build_message, send_bulk, send_email, user_language
from Users.i18n import tr
from Users.templatetags.language_tags import MONTH_LABELS

# Поля, изменения которых важны участникам: (поле, подпись ru, подпись en)
TRACKED_FIELDS = (
    ('name', 'Название', 'Name'),
    ('date', 'Дата', 'Date'),
    ('time', 'Время', 'Time'),
    ('location', 'Место', 'Location'),
)


def snapshot(event):
    return {field: getattr(event, field) for field, _ru, _en in TRACKED_FIELDS}


def changed_fields(before, event):
    return [field for field, _ru, _en in TRACKED_FIELDS if before.get(field) != getattr(event, field)]


def _format_value(field, value, language):
    if value in (None, ''):
        return ''
    if field == 'date':
        months = MONTH_LABELS.get(language, MONTH_LABELS['ru'])
        sep = '. ' if language == 'cs' else ' '
        return f'{value.day}{sep}{months[value.month]} {value.year}'
    if field == 'time':
        return value.strftime('%H:%M')
    return str(value)


def _recipients(event, exclude_creator=True):
    """Активные участники с включёнными уведомлениями."""
    registrations = event.registrations.select_related('user').filter(
        user__is_active=True, user__email_notifications=True,
    ).exclude(user__email='')
    if exclude_creator and event.creator_id:
        registrations = registrations.exclude(user_id=event.creator_id)
    return [registration.user for registration in registrations]


def _event_url(event, request=None):
    path = reverse('Events:event_detail', args=[event.id])
    if event.is_private and event.access_token:
        path += f'?token={event.access_token}'
    return request.build_absolute_uri(path) if request else absolute_url(path)


def _calendar_url(event, request=None):
    path = reverse('Events:event_calendar', args=[event.id])
    if event.is_private and event.access_token:
        path += f'?token={event.access_token}'
    return request.build_absolute_uri(path) if request else absolute_url(path)


def notify_registered(event, user, request=None):
    if not user.email or not user.email_notifications or user.id == event.creator_id:
        return False
    return send_email(
        to=user.email,
        template='event_registered',
        subject=('Вы записались: ', "You're going: ", event.name),
        context={'event': event, 'event_url': _event_url(event, request), 'calendar_url': _calendar_url(event, request)},
        language=user_language(user),
        fail_silently=True,
    )


def notify_created(event, request=None):
    """Письмо организатору: мероприятие создано (с приватной ссылкой, если оно приватное)."""
    user = event.creator
    if not user or not user.email or not user.email_notifications:
        return False
    edit_path = reverse('Events:edit_event', args=[event.id])
    return send_email(
        to=user.email,
        template='event_created',
        subject=('Мероприятие создано: ', 'Event created: ', event.name),
        context={
            'event': event,
            'event_url': _event_url(event, request),
            'calendar_url': _calendar_url(event, request),
            'edit_url': request.build_absolute_uri(edit_path) if request else absolute_url(edit_path),
        },
        language=user_language(user),
        fail_silently=True,
    )


def notify_updated(event, before, fields, request=None):
    if not fields:
        return 0
    event_url = _event_url(event, request)
    messages = []
    for user in _recipients(event):
        language = user_language(user)
        changes = [
            {
                'label': tr(language, ru, en),
                'old': _format_value(field, before.get(field), language),
                'new': _format_value(field, getattr(event, field), language),
            }
            for field, ru, en in TRACKED_FIELDS if field in fields
        ]
        messages.append(build_message(
            to=user.email,
            template='event_updated',
            subject=('Изменения в мероприятии: ', 'Event update: ', event.name),
            context={'event': event, 'event_url': event_url, 'changes': changes,
                     'calendar_url': _calendar_url(event, request)},
            language=language,
        ))
    return send_bulk(messages)


def collect_cancel_messages(event, request=None):
    """Собирает письма об отмене ДО удаления события (после удаления участников уже не найти)."""
    events_path = reverse('Events:event_list')
    events_url = request.build_absolute_uri(events_path) if request else absolute_url(events_path)
    return [
        build_message(
            to=user.email,
            template='event_cancelled',
            subject=('Мероприятие отменено: ', 'Event cancelled: ', event.name),
            context={'event': event, 'events_url': events_url},
            language=user_language(user),
        )
        for user in _recipients(event)
    ]


def send_reminders(events):
    """Напоминания «завтра мероприятие». Возвращает (событий, писем)."""
    sent_events = sent_messages = 0
    for event in events:
        event_url = _event_url(event)
        messages = [
            build_message(
                to=user.email,
                template='event_reminder',
                subject=('Завтра: ', 'Tomorrow: ', event.name),
                context={'event': event, 'event_url': event_url, 'calendar_url': _calendar_url(event)},
                language=user_language(user),
            )
            for user in _recipients(event, exclude_creator=False)
        ]
        sent_messages += send_bulk(messages)
        event.reminder_sent = True
        event.save(update_fields=['reminder_sent'])
        sent_events += 1
    return sent_events, sent_messages
