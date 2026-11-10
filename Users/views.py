import json
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.core.cache import cache
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.hashers import check_password, make_password
from django.shortcuts import get_object_or_404, render, HttpResponseRedirect, redirect
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from Users.models import FriendRequest, User
from Users.forms import UserLoginForm, UserRegistrationForm, UserProfileForm
from django.contrib import auth
from django.urls import reverse
from django.contrib import messages
from Events.models import Event, EventRegistration, EventType
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.views.decorators.http import require_POST
from django.utils.http import url_has_allowed_host_and_scheme
from Users.i18n import SUPPORTED_LANGUAGES, get_language, tr
from Users.emails import send_email
from Users.images import process_image, replace_image
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
from django.core.paginator import Paginator
from datetime import date, datetime
from calendar import monthcalendar, month_name
CONFIRM_CODE_MAX_ATTEMPTS = 5
CONFIRM_CODE_TTL_MINUTES = 30
RESEND_COOLDOWN_SECONDS = 60
CONFIRM_CODE_LOCK_SECONDS = 15 * 60


def set_language(request, lang_code):
    if lang_code not in SUPPORTED_LANGUAGES:
        lang_code = 'ru'
    request.session['language'] = lang_code
    if request.user.is_authenticated and request.user.language != lang_code:
        request.user.language = lang_code
        request.user.save(update_fields=['language'])
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or ''
    if not url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
    ):
        next_url = reverse('base')
    return redirect(next_url)

def build_event_calendar(user, month=None, year=None):
    """Создаёт календарь с событиями пользователя для месяца."""
    if month is None:
        month = datetime.now().month
    if year is None:
        year = datetime.now().year

    # Получаем события пользователя на этот месяц
    registered_events = EventRegistration.objects.filter(user=user).exclude(
        event__creator=user
    ).values_list('event', flat=True)
    events = Event.objects.filter(
        id__in=registered_events,
        date__year=year,
        date__month=month
    )

    # Создаём словарь дней с событиями
    events_by_day = {}
    for event in events:
        day = event.date.day
        if day not in events_by_day:
            events_by_day[day] = []
        events_by_day[day].append(event)

    # Получаем календарную сетку
    cal = monthcalendar(year, month)

    return {
        'calendar': cal,
        'month': month_name[month],
        'year': year,
        'events_by_day': events_by_day
    }

def base(request):
    latest_events = Event.objects.filter(
        date__gte=date.today(),
        is_private=False,
    ).order_by('date', 'time')[:6]
    language = get_language(request)
    event_types = EventType.localized_choices(language) or [
        (code, label) for code, label in Event.EVENT_TYPE_LABELS.get(language, Event.EVENT_TYPE_LABELS['ru']).items()
    ]

    return render(request, 'Users/base.html', {
        'latest_events': latest_events,
        'event_types': event_types,
        'is_home': True,
    })

def login(request):
    language = get_language(request)
    if request.method == "POST":
        form = UserLoginForm(data=request.POST, language=language)
        if form.is_valid():
            username = request.POST['username']
            password = request.POST['password']
            user = auth.authenticate(username=username, password=password)
            if user:
                auth.login(request, user)
                next_url = request.POST.get('next', '')
                if not url_has_allowed_host_and_scheme(
                    next_url, allowed_hosts={request.get_host()}, require_https=request.is_secure()
                ):
                    next_url = reverse('base')
                return HttpResponseRedirect(next_url)
    else:
        form = UserLoginForm(language=language)
    context = {'form': form, 'next': request.POST.get('next') or request.GET.get('next', '')}
    return render(request, 'Users/login.html', context)

def confirm_email(request, uidb64, token):
    language = get_language(request)
    user = None
    try:
        user_id = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=user_id)
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        pass

    if user and default_token_generator.check_token(user, token):
        user.is_active = True
        user.save(update_fields=['is_active'])
        return render(request, 'Users/email_confirmed.html', {'language': language})

    return render(request, 'Users/email_confirmed.html', {
        'language': language,
        'invalid': True,
    }, status=400)

def confirm_email_code(request):
    language = get_language(request)
    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        code = request.POST.get('code', '').strip()
        attempts_key = f'confirm-code-attempts:{email.lower()}'
        attempts = cache.get(attempts_key, 0)
        if attempts >= CONFIRM_CODE_MAX_ATTEMPTS:
            return render(request, 'Users/email_confirm_code.html', {
                'language': language,
                'error': tr(language, 'Слишком много попыток. Попробуйте через 15 минут.',
                            'Too many attempts. Try again in 15 minutes.'),
                'email': email,
            }, status=429)
        cache.set(attempts_key, attempts + 1, CONFIRM_CODE_LOCK_SECONDS)
        user = User.objects.filter(email__iexact=email, is_active=False).first()
        code_expired = bool(
            user and user.email_confirmation_sent_at
            and timezone.now() - user.email_confirmation_sent_at > timedelta(minutes=CONFIRM_CODE_TTL_MINUTES)
        )
        if user and not code_expired and len(code) == 6 and code.isdigit() and check_password(
            code, user.email_confirmation_code_hash
        ):
            user.is_active = True
            user.email_confirmation_code_hash = ''
            user.save(update_fields=['is_active', 'email_confirmation_code_hash'])
            cache.delete(attempts_key)
            return render(request, 'Users/email_confirmed.html', {'language': language})
        if code_expired:
            error = tr(language, 'Срок действия кода истёк. Отправьте новый код.', 'The code has expired. Send a new one.')
        else:
            error = tr(language, 'Неверный email или код подтверждения.', 'Invalid email or confirmation code.')
    return render(request, 'Users/email_confirm_code.html', {
        'language': language,
        'error': error,
        'email': request.POST.get('email') or request.GET.get('email', ''),
        'resend_cooldown': RESEND_COOLDOWN_SECONDS,
    })


def send_confirmation_email(request, user, language):
    """Генерирует новый код и ссылку подтверждения и отправляет письмо. True — если ушло."""
    code = f'{secrets.randbelow(1000000):06d}'
    user.email_confirmation_code_hash = make_password(code)
    user.email_confirmation_sent_at = timezone.now()
    user.save(update_fields=['email_confirmation_code_hash', 'email_confirmation_sent_at'])

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    confirm_url = request.build_absolute_uri(
        reverse('Users:confirm_email', kwargs={'uidb64': uid, 'token': token})
    )
    return send_email(
        to=user.email,
        template='confirm_email',
        subject=('Подтвердите email в EventTown', 'Confirm your EventTown email'),
        context={
            'username': user.username,
            'code': code,
            'confirm_url': confirm_url,
            'expires_minutes': CONFIRM_CODE_TTL_MINUTES,
        },
        language=language,
        fail_silently=True,
    )


@require_POST
def resend_confirmation(request):
    """Повторная отправка кода. Не раскрывает, есть ли такой email в базе."""
    language = get_language(request)
    email = request.POST.get('email', '').strip()
    cooldown_key = f'confirm-resend:{email.lower()}'
    if email and not cache.get(cooldown_key):
        cache.set(cooldown_key, True, RESEND_COOLDOWN_SECONDS)
        user = User.objects.filter(email__iexact=email, is_active=False).first()
        if user:
            send_confirmation_email(request, user, user.language or language)
            cache.delete(f'confirm-code-attempts:{email.lower()}')
        messages.success(request, tr(
            language,
            'Если аккаунт с таким email ждёт подтверждения, мы отправили новый код.',
            'If an account with this email is waiting for confirmation, we sent a new code.',
        ))
    elif email:
        messages.warning(request, tr(
            language,
            'Новый код можно запросить раз в минуту.',
            'You can request a new code once a minute.',
        ))
    url = reverse('Users:confirm_email_code')
    return HttpResponseRedirect(f'{url}?{urlencode({"email": email})}' if email else url)

def registration(request):
    if request.method == "POST":
        form = UserRegistrationForm(data=request.POST, language=get_language(request))
        if form.is_valid():
            language = get_language(request)
            user = form.save(commit=False)
            user.is_active = False
            user.language = language
            user.save()

            if send_confirmation_email(request, user, language):
                messages.success(
                    request,
                    tr(language, 'Проверьте почту и подтвердите email.', 'Check your email and confirm your address.')
                )
            else:
                messages.warning(request, tr(
                    language,
                    'Аккаунт создан, но письмо не отправилось. Нажмите «Отправить код ещё раз».',
                    'Account created, but the email failed to send. Press "Send the code again".',
                ))
            confirm_url = reverse('Users:confirm_email_code')
            return HttpResponseRedirect(f'{confirm_url}?{urlencode({"email": user.email})}')
    else:
        form = UserRegistrationForm(language=get_language(request))
    context = {'form': form}
    return render(request, 'Users/registration.html', context)

# def event(request):
#     return render(request, 'Users/../Events/templates/event.html')

def about(request):
    return render(request, 'Users/about.html', {
        'contact_email': settings.CONTACT_EMAIL,
    })

@login_required(login_url='Users:login')
def profile(request):
    if request.method == "POST":
        form = UserProfileForm(instance= request.user, data=request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('Users:profile'))
    else:
        form = UserProfileForm(instance=request.user)

    my_events = list(
        Event.objects.filter(creator=request.user)
        .annotate(reg_count=Count('registrations'))
        .order_by('-date', '-time')
    )

    # Получаем события, на которые зарегистрирован пользователь
    registered_events = EventRegistration.objects.filter(user=request.user).exclude(
        event__creator=request.user
    ).select_related('event').order_by('event__date', 'event__time')

    # Получаем месяц и год для календаря
    month = request.GET.get('month', None)
    year = request.GET.get('year', None)
    if month:
        month = int(month)
    if year:
        year = int(year)

    calendar_data = build_event_calendar(request.user, month, year)

    # Подготавливаем данные для client-side календаря (весь год)
    registered_events_data = []
    for registration in EventRegistration.objects.filter(user=request.user).exclude(
        event__creator=request.user
    ).select_related('event'):
        event = registration.event
        if event.date:
            registered_events_data.append({
                'id': event.id,
                'name': event.name,
                'date': event.date.isoformat(),
                'time': event.time.strftime('%H:%M') if event.time else '',
                'location': event.location,
                'registered': True
            })

    current_month = month or datetime.now().month
    current_year = year or datetime.now().year

    context = {
        'form': form,
        'my_events': my_events,
        'registered_events': registered_events,
        'calendar_data': calendar_data,
        'current_month': current_month,
        'current_year': current_year,
        'registered_events_json': json.dumps(registered_events_data, ensure_ascii=False)
    }
    context['friends'] = User.objects.filter(
        Q(sent_friend_requests__to_user=request.user, sent_friend_requests__status='accepted') |
        Q(received_friend_requests__from_user=request.user, received_friend_requests__status='accepted')
    ).distinct()
    context['incoming_friend_requests'] = FriendRequest.objects.filter(
        to_user=request.user, status='pending'
    ).select_related('from_user')
    return render(request, 'Users/profile.html', context)


@login_required(login_url='Users:login')
@require_POST
def update_avatar(request):
    language = get_language(request)
    user = request.user
    if request.POST.get('remove_avatar'):
        if user.avatar:
            replace_image(user, 'avatar', None)
            user.save(update_fields=['avatar'])
            messages.success(request, tr(language, 'Фото удалено.', 'Photo removed.'))
        return redirect('Users:profile')
    upload = request.FILES.get('avatar')
    if not upload:
        messages.error(request, tr(language, 'Выберите фото.', 'Choose a photo.'))
        return redirect('Users:profile')
    try:
        processed = process_image(upload, 'avatar', language)
    except ValidationError as exc:
        messages.error(request, exc.messages[0])
        return redirect('Users:profile')
    replace_image(user, 'avatar', processed)
    user.save(update_fields=['avatar'])
    messages.success(request, tr(language, 'Фото обновлено.', 'Photo updated.'))
    return redirect('Users:profile')


def public_profile(request, username):
    profile_user = get_object_or_404(User, username=username, is_active=True)
    if profile_user.is_profile_private and request.user != profile_user:
        return render(request, 'Users/public_profile.html', {
            'profile_user': profile_user,
            'is_private': True,
        })
    events = Event.objects.filter(creator=profile_user)
    if request.user != profile_user:
        events = events.filter(is_private=False)
    return render(request, 'Users/public_profile.html', {
        'profile_user': profile_user,
        'events': events.order_by('-date', '-time'),
        'is_private': False,
        'is_friend': request.user.is_authenticated and request.user != profile_user and FriendRequest.objects.filter(
            Q(from_user=request.user, to_user=profile_user) | Q(from_user=profile_user, to_user=request.user),
            status='accepted',
        ).exists(),
    })


@login_required(login_url='Users:login')
def friends(request):
    query = request.GET.get('q', '').strip()
    users_queryset = User.objects.filter(is_active=True).exclude(pk=request.user.pk).order_by('username')
    if query:
        users_queryset = users_queryset.filter(username__icontains=query)
    users_page = Paginator(users_queryset, 8).get_page(request.GET.get('page'))
    users = users_page.object_list
    relationship_statuses = {}
    for person in users:
        relation = FriendRequest.objects.filter(
            Q(from_user=request.user, to_user=person) |
            Q(from_user=person, to_user=request.user)
        ).order_by('-status', '-created_at').first()
        if relation:
            if relation.status == 'accepted':
                relationship_statuses[person.id] = 'friend'
            elif relation.from_user_id == request.user.id:
                relationship_statuses[person.id] = 'sent'
            else:
                relationship_statuses[person.id] = 'received'
        else:
            relationship_statuses[person.id] = 'none'
    requests = FriendRequest.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).select_related('from_user', 'to_user').order_by('-created_at')
    incoming = [r for r in requests if r.to_user_id == request.user.id and r.status == 'pending']
    history = [r for r in requests if r not in incoming]
    friend_users = list(User.objects.filter(
        Q(sent_friend_requests__to_user=request.user, sent_friend_requests__status='accepted') |
        Q(received_friend_requests__from_user=request.user, received_friend_requests__status='accepted')
    ).distinct().order_by('username'))
    # Ближайшее публичное событие каждого друга — «куда идёт»
    next_events = {}
    upcoming = (
        EventRegistration.objects
        .filter(user__in=friend_users, event__is_private=False, event__date__gte=timezone.localdate())
        .select_related('event')
        .order_by('event__date', 'event__time')
    )
    for registration in upcoming:
        next_events.setdefault(registration.user_id, registration.event)
    for friend in friend_users:
        friend.next_event = next_events.get(friend.pk)
    if query or request.GET.get('page') or request.GET.get('tab') == 'find':
        active_tab = 'all'
    elif request.GET.get('tab') == 'requests':
        active_tab = 'requests'
    else:
        active_tab = 'friends' if friend_users else 'all'
    return render(request, 'Users/friends.html', {
        'users': users,
        'users_page': users_page,
        'query': query,
        'friend_requests': history,
        'incoming_requests': incoming,
        'friend_users': friend_users,
        'relationship_statuses': relationship_statuses,
        'active_tab': active_tab,
    })


@login_required(login_url='Users:login')
@require_POST
def send_friend_request(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target != request.user:
        existing = FriendRequest.objects.filter(
            from_user=request.user, to_user=target
        ).first()
        reverse_request = FriendRequest.objects.filter(
            from_user=target, to_user=request.user
        ).first()
        if existing and existing.status == 'accepted':
            return redirect('Users:friends')
        if reverse_request and reverse_request.status == 'pending':
            reverse_request.status = 'accepted'
            reverse_request.save(update_fields=['status'])
            if existing:
                existing.delete()
        else:
            FriendRequest.objects.update_or_create(
                from_user=request.user,
                to_user=target,
                defaults={'status': 'pending'},
            )
    return redirect('Users:friends')


@login_required(login_url='Users:login')
@require_POST
def respond_friend_request(request, request_id, action):
    friend_request = get_object_or_404(
        FriendRequest, pk=request_id, to_user=request.user, status='pending'
    )
    friend_request.status = 'accepted' if action == 'accept' else 'declined'
    friend_request.save(update_fields=['status'])
    return redirect('Users:profile')


@login_required(login_url='Users:login')
@require_POST
def remove_friend(request, user_id):
    FriendRequest.objects.filter(
        Q(from_user=request.user, to_user_id=user_id) |
        Q(from_user_id=user_id, to_user=request.user),
        status='accepted',
    ).delete()
    return redirect('Users:profile')

@require_POST
def logout(request):
    auth.logout(request)
    return HttpResponseRedirect(reverse('base'))