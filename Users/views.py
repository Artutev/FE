import json
import secrets
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.contrib.auth.hashers import check_password, make_password
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404, render, HttpResponseRedirect, redirect
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from Users.models import FriendRequest, User
from Users.forms import UserLoginForm, UserRegistrationForm, UserProfileForm
from django.contrib import auth
from django.urls import reverse
from django.contrib import messages
from Events.models import Event, EventRegistration
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views.decorators.http import require_POST
from datetime import date, datetime
from calendar import monthcalendar, month_name
# Create your views here.


def set_language(request, lang_code):
    if lang_code not in ('ru', 'en'):
        lang_code = 'ru'
    request.session['language'] = lang_code
    next_url = request.GET.get('next') or request.META.get('HTTP_REFERER') or reverse('base')
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
    ).order_by('date', 'time')[:2]

    return render(request, 'Users/base.html', {'latest_events': latest_events, 'is_home': True})

def login(request):
    if request.method == "POST":
        form = UserLoginForm(data= request.POST)
        if form.is_valid():
            username = request.POST['username']
            password = request.POST['password']
            user = auth.authenticate(username=username, password=password)
            if user:
                auth.login(request, user)
                return HttpResponseRedirect(reverse('base'))
        else:
            messages.error(request, 'Неправильное имя пользователя или пароль.')
    else:
        form = UserLoginForm(language=request.session.get('language', 'ru'))
    context = {'form': form}
    return render(request, 'Users/login.html', context)

def confirm_email(request, uidb64, token):
    language = request.session.get('language', 'ru')
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
    language = request.session.get('language', 'ru')
    error = None
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        code = request.POST.get('code', '').strip()
        user = User.objects.filter(email__iexact=email, is_active=False).first()
        if user and len(code) == 6 and code.isdigit() and check_password(
            code, user.email_confirmation_code_hash
        ):
            user.is_active = True
            user.email_confirmation_code_hash = ''
            user.save(update_fields=['is_active', 'email_confirmation_code_hash'])
            return render(request, 'Users/email_confirmed.html', {'language': language})
        error = (
            'Неверный email или код подтверждения.'
            if language == 'ru'
            else 'Invalid email or confirmation code.'
        )
    return render(request, 'Users/email_confirm_code.html', {
        'language': language,
        'error': error,
    })

def registration(request):
    if request.method == "POST":
        form = UserRegistrationForm(data=request.POST, language=request.session.get('language', 'ru'))
        if form.is_valid():
            user = form.save(commit=False)
            user.is_active = False
            confirmation_code = f'{secrets.randbelow(1000000):06d}'
            user.email_confirmation_code_hash = make_password(confirmation_code)
            user.save()

            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            confirmation_url = request.build_absolute_uri(
                reverse('Users:confirm_email', kwargs={'uidb64': uid, 'token': token})
            )
            language = request.session.get('language', 'ru')
            subject = 'Подтвердите email в EventHub' if language == 'ru' else 'Confirm your EventHub email'
            message = render_to_string('Users/email_confirmation.txt', {
                'confirmation_url': confirmation_url,
                'confirmation_code': confirmation_code,
                'language': language,
                'username': user.username,
            })
            send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])
            messages.success(
                request,
                'Проверьте почту и подтвердите email.'
                if language == 'ru'
                else 'Check your email and confirm your address.'
            )
            confirm_url = reverse('Users:confirm_email_code')
            return HttpResponseRedirect(f'{confirm_url}?{urlencode({"email": user.email})}')
        else:
            messages.error(request, 'Чет не так')
    else:
        form = UserRegistrationForm(language=request.session.get('language', 'ru'))
    context = {'form': form}
    return render(request, 'Users/registration.html', context)

# def event(request):
#     return render(request, 'Users/../Events/templates/event.html')

def about(request):
    return render(request, 'Users/about.html')

@login_required(login_url='Users:login')
def profile(request):
    if request.method == "POST":
        form = UserProfileForm(instance= request.user, data=request.POST)
        if form.is_valid():
            form.save()
            return HttpResponseRedirect(reverse('Users:profile'))
        else:
            print(form.errors)
    else:
        form = UserProfileForm(instance=request.user)
    
    my_events = Event.objects.filter(creator=request.user)
    
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


def public_profile(request, username):
    profile_user = get_object_or_404(User, username=username, is_active=True)
    if profile_user.is_profile_private and request.user != profile_user:
        return render(request, 'Users/public_profile.html', {
            'profile_user': profile_user,
            'is_private': True,
        })
    return render(request, 'Users/public_profile.html', {
        'profile_user': profile_user,
        'events': Event.objects.filter(creator=profile_user).order_by('-date', '-time'),
        'is_private': False,
    })


@login_required(login_url='Users:login')
def friends(request):
    query = request.GET.get('q', '').strip()
    users = User.objects.exclude(pk=request.user.pk)
    if query:
        users = users.filter(username__icontains=query)
    requests = FriendRequest.objects.filter(
        Q(from_user=request.user) | Q(to_user=request.user)
    ).select_related('from_user', 'to_user')
    return render(request, 'Users/friends.html', {
        'users': users,
        'query': query,
        'friend_requests': requests,
    })


@login_required(login_url='Users:login')
@require_POST
def send_friend_request(request, user_id):
    target = get_object_or_404(User, pk=user_id)
    if target != request.user:
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

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect(reverse('base'))