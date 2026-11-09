from datetime import date

from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.http import HttpResponse, Http404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.db.models import Q
from django.urls import reverse
from Events.models import Event, EventType
from Events.forms import EventForm
from Users.models import FriendRequest
from Users.i18n import get_language, tr

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
        form = EventForm(request.POST, language=language)
        if form.is_valid():
            event = form.save(commit=False)
            event.creator = request.user
            event.save()
            # Автоматически регистрируем создателя на своё событие
            from Events.models import EventRegistration
            EventRegistration.objects.get_or_create(user=request.user, event=event)

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

    context = {
        'event': event,
        'is_registered': is_registered,
        'registration_count': registration_count,
        'registered_friends': registered_friends,
        'private_link': private_link,
        'token_param': token_param
    }
    return render(request, 'Events/eventDetail.html', context)

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
        form = EventForm(request.POST, instance=event, language=language)
        if form.is_valid():
            form.save()
            messages.success(request, tr(language, 'Изменения сохранены.', 'Event updated.'))
            return redirect('Events:event_detail', event_id=event.id)
    else:
        form = EventForm(instance=event, language=language)

    return render(request, 'Events/eventEdit.html', {'form': form, 'event': event})


@login_required(login_url='Users:login')
def delete_event(request, event_id):
    event = get_object_or_404(Event, id=event_id, creator=request.user)

    if request.method == 'POST':
        event.delete()
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
    EventRegistration.objects.get_or_create(user=request.user, event=event)
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