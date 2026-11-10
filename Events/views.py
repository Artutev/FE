from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse, Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.urls import reverse
from Events.models import Event, EventType, InvitationCard
from Events.forms import EventForm, InvitationCardForm
from Events import card_designs
from Users.models import FriendRequest
from Users.i18n import get_language, tr
from Events import invites, notifications
from Users.emails import in_background, send_bulk

def _has_access(request, event):
    """Приватное событие доступно только создателю или по ссылке с токеном."""
    if not event.is_private:
        return True
    if request.user.is_authenticated and request.user == event.creator:
        return True
    token = request.POST.get('token') or request.GET.get('token')
    return bool(token) and token == event.access_token


def _detail_redirect(event):
    url = reverse('Events:event_detail', args=[event.id])
    if event.is_private and event.access_token:
        url += f'?token={event.access_token}'
    return redirect(url)


@login_required(login_url='Users:login')
def create_event(request):
    language = get_language(request)
    if request.method == 'POST':
        form = EventForm(request.POST, request.FILES, language=language)
        if form.is_valid():
            event = form.save(commit=False)
            event.creator = request.user
            event.save()
            # Автоматически регистрируем создателя на своё событие
            from Events.models import EventRegistration
            EventRegistration.objects.get_or_create(user=request.user, event=event)
            in_background(notifications.notify_created, event, request=request)
            request.session['card_prompt'] = event.id

            messages.success(request, tr(language, 'Мероприятие создано.', 'Event created.'))
            redirect_url = reverse('Events:event_detail', args=[event.id])
            if event.is_private and event.access_token:
                redirect_url += f'?token={event.access_token}'
            return redirect(redirect_url)
    else:
        form = EventForm(language=language)
    context = {'form': form}

    return render(request, 'Events/event.html', context)

def event_list(request):
    # Показываем только мероприятия, которые еще не прошли
    events = Event.objects.filter(date__gte=date.today(), is_private=False).order_by('date', 'time')

    # Фильтр по типу события
    event_type = request.GET.get('type', '')
    if event_type and event_type != 'all':
        events = events.filter(event_type=event_type)

    # Поиск мероприятий (работаем через queryset, поддерживает кириллицу)
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        events = events.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    context = {
        'events': events,
        'search_query': search_query,
        'event_type': event_type,
        'event_types': EventType.localized_choices(get_language(request))
    }
    return render(request, 'Events/eventList.html', context)


def event_archive(request):
    """Показывает прошедшие/архивные мероприятия."""
    today = date.today()
    events = Event.objects.filter(date__lt=today, is_private=False).order_by('-date', '-time')

    event_type = request.GET.get('type', '')
    if event_type and event_type != 'all':
        events = events.filter(event_type=event_type)

    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        events = events.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )

    context = {
        'events': events,
        'search_query': search_query,
        'event_type': event_type,
        'event_types': EventType.localized_choices(get_language(request))
    }
    return render(request, 'Events/eventArchive.html', context)

def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not _has_access(request, event):
        raise Http404()

    is_registered = False
    if request.user.is_authenticated:
        from Events.models import EventRegistration
        is_registered = EventRegistration.objects.filter(user=request.user, event=event).exists()

    # Получаем количество зарегистрированных
    from Events.models import EventRegistration
    registration_count = event.registrations.count()
    friend_relations = FriendRequest.objects.filter(
        Q(from_user=request.user, status='accepted') |
        Q(to_user=request.user, status='accepted')
    ).values_list('from_user_id', 'to_user_id') if request.user.is_authenticated else []
    friend_user_ids = {
        user_id
        for relation in friend_relations
        for user_id in relation
        if request.user.is_authenticated and user_id != request.user.id
    }
    registered_friends = event.registrations.filter(
        user_id__in=friend_user_ids
    ).select_related('user')

    private_link = None
    token_param = ''
    token = request.GET.get('token')
    if event.is_private:
        if request.user == event.creator and event.access_token:
            private_link = request.build_absolute_uri(
                reverse('Events:event_detail', args=[event.id]) + f'?token={event.access_token}'
            )
            token_param = f'?token={event.access_token}'
        elif token == event.access_token:
            token_param = f'?token={token}'

    can_invite = invites.can_invite(request.user, event, True)
    is_creator = request.user.is_authenticated and request.user.id == event.creator_id
    event_card = InvitationCard.objects.filter(event=event).only('code').first()
    # Сразу после создания — предложить оформить пригласительное (один раз)
    show_card_prompt = is_creator and not event_card and request.session.pop('card_prompt', None) == event.id
    context = {
        'event': event,
        'is_creator': is_creator,
        'event_card': event_card,
        'show_card_prompt': show_card_prompt,
        'can_invite': can_invite,
        'invite_friends': invites.invite_candidates(request.user, event) if can_invite else [],
        'is_registered': is_registered,
        'registration_count': registration_count,
        'registered_friends': registered_friends,
        'private_link': private_link,
        'token_param': token_param
    }
    return render(request, 'Events/eventDetail.html', context)

def event_calendar(request, event_id):
    """Файл .ics — «Добавить в календарь» (Google, Apple, Outlook)."""
    from Events.ics import build_ics

    event = get_object_or_404(Event, id=event_id)
    if not _has_access(request, event):
        raise Http404()
    path = reverse('Events:event_detail', args=[event.id])
    if event.is_private and event.access_token:
        path += f'?token={event.access_token}'
    response = HttpResponse(
        build_ics(event, request.build_absolute_uri(path), request.get_host()),
        content_type='text/calendar; charset=utf-8',
    )
    response['Content-Disposition'] = f'attachment; filename="event-{event.id}.ics"'
    return response


def download_invitation(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not _has_access(request, event):
        raise Http404()
    if event.event_type != 'wedding':
        return redirect('Events:event_detail', event_id=event_id)

    filename = f"invite-{event.id}.html"
    content = render_to_string('Events/invitation.html', {'event': event}, request=request)
    response = HttpResponse(content, content_type='text/html; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response

@login_required(login_url='Users:login')
def edit_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, creator=request.user)
    language = get_language(request)

    if request.method == 'POST':
        before = notifications.snapshot(event)
        form = EventForm(request.POST, request.FILES, instance=event, language=language)
        if form.is_valid():
            event = form.save(commit=False)
            changed = notifications.changed_fields(before, event)
            if 'date' in changed or 'time' in changed:
                event.reminder_sent = False
            event.save()
            in_background(notifications.notify_updated, event, before, changed, request=request)
            messages.success(request, tr(language, 'Изменения сохранены.', 'Event updated.'))
            return redirect('Events:event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event, language=language)

    return render(request, 'Events/eventEdit.html', {'form': form, 'event': event})


@login_required(login_url='Users:login')
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, creator=request.user)

    if request.method == 'POST':
        cancel_messages = notifications.collect_cancel_messages(event, request=request)
        event.delete()
        in_background(send_bulk, cancel_messages)
        messages.success(request, tr(get_language(request), 'Мероприятие удалено.', 'Event deleted.'))
        return redirect('Users:profile')
    context = {'event': event}

    return render(request, 'Events/eventDeleteConfirm.html', context)


@login_required(login_url='Users:login')
@require_POST
def register_event(request, event_id):
    """Зарегистрировать пользователя на событие."""
    event = get_object_or_404(Event, id=event_id)
    if not _has_access(request, event):
        raise Http404()

    if event.has_passed:
        messages.error(request, tr(
            get_language(request),
            'Регистрация закрыта: мероприятие уже прошло.',
            'Registration is closed: the event has already passed.',
        ))
        return _detail_redirect(event)

    from Events.models import EventRegistration
    _registration, created = EventRegistration.objects.get_or_create(user=request.user, event=event)
    if created:
        in_background(notifications.notify_registered, event, request.user, request=request)
    return _detail_redirect(event)


@login_required(login_url='Users:login')
@require_POST
def invite_friends(request, event_id):
    """Позвать выбранных друзей: каждому придёт приглашение со ссылкой в личный чат."""
    event = get_object_or_404(Event, id=event_id)
    if not _has_access(request, event):
        raise Http404()
    language = get_language(request)
    if not invites.can_invite(request.user, event, True):
        messages.error(request, tr(language, 'Приглашать на прошедшее мероприятие нельзя.', "You can't invite people to a past event."))
        return _detail_redirect(event)
    ids = []
    for raw in request.POST.getlist('friends'):
        try:
            ids.append(int(raw))
        except (TypeError, ValueError):
            continue
    sent = invites.send_invites(request.user, event, ids, request, language)
    if sent:
        messages.success(request, tr(language, 'Приглашения отправлены: ', 'Invitations sent: ') + str(sent))
    else:
        messages.info(request, tr(language, 'Выберите друзей, которых ещё не приглашали.', "Pick friends you haven't invited yet."))
    return _detail_redirect(event)


@login_required(login_url='Users:login')
@require_POST
def unregister_event(request, event_id):
    """Отменить регистрацию пользователя на событие."""
    event = get_object_or_404(Event, id=event_id)
    if not _has_access(request, event):
        raise Http404()

    from Events.models import EventRegistration
    EventRegistration.objects.filter(user=request.user, event=event).delete()
    return _detail_redirect(event)


def _card_url(card, request=None):
    path = reverse('invite_card', args=[card.code])
    return request.build_absolute_uri(path) if request else path


def _card_context(card, language):
    return {'card': card, 'card_when': card_designs.when(card.event, language)}


@login_required(login_url='Users:login')
def card_editor(request, event_id):
    """Конструктор пригласительного — только для организатора."""
    event = get_object_or_404(Event, id=event_id)
    if event.creator_id != request.user.id:
        raise Http404()
    language = get_language(request)
    card = InvitationCard.objects.filter(event=event).first() or InvitationCard.initial_for(event, language)
    if request.method == 'POST':
        form = InvitationCardForm(request.POST, instance=card, event=event)
        if form.is_valid():
            card = form.save(commit=False)
            card.event = event
            card.save()
            messages.success(request, tr(language, 'Пригласительное сохранено.', 'Invitation saved.'))
            return redirect('invite_card', code=card.code)
        card = form.instance
    else:
        form = InvitationCardForm(instance=card, event=event)

    # Мини-превью всех шаблонов на текущих текстах
    template_previews = []
    for key in card_designs.TEMPLATES:
        preview = InvitationCard(
            event=event, template=key, palette=card_designs.first_palette(key),
            font=card_designs.TEMPLATES[key]['font'], background='decor', format='story',
            title=card.title or event.name, subtitle=card.subtitle, message=card.message,
        )
        template_previews.append({'key': key, 'name': tr(language, *card_designs.TEMPLATES[key]['name']),
                                  **_card_context(preview, language)})

    def options(source):
        return [{'key': key, 'name': tr(language, value[0], value[1])} for key, value in source.items()]

    return render(request, 'Events/card_editor.html', {
        **_card_context(card, language),
        'event': event,
        'form': form,
        'is_saved': bool(card.pk),
        'template_previews': template_previews,
        'palettes': [
            {'key': slug, 'name': tr(language, p[0], p[1]), **card_designs.palette(card.template, slug)}
            for slug, p in card_designs.TEMPLATES[card.template]['palettes'].items()
        ],
        'fonts': [{'key': k, 'display': f[0], 'name': tr(language, f[2], f[3])} for k, f in card_designs.FONTS.items()],
        'formats': options(card_designs.FORMATS),
        'backgrounds': options(card_designs.BACKGROUNDS),
        'catalog': card_designs.catalog_for_js(language),
        'fonts_url': card_designs.GOOGLE_FONTS_URL,
        'default_accent': card_designs.palette(card.template, card.palette)['accent'],
    })


def card_public(request, code):
    """Публичная страница пригласительного: открывается по ссылке и без входа (код случайный)."""
    card = get_object_or_404(InvitationCard.objects.select_related('event', 'event__creator'), code=code)
    event = card.event
    language = get_language(request)
    event_path = reverse('Events:event_detail', args=[event.id])
    if event.is_private and event.access_token:
        event_path += f'?token={event.access_token}'
    return render(request, 'Events/card_public.html', {
        **_card_context(card, language),
        'event': event,
        'event_url': event_path,
        'card_link': _card_url(card, request),
        'is_owner': request.user.is_authenticated and request.user.id == event.creator_id,
        'fonts_url': card_designs.GOOGLE_FONTS_URL,
    })
