from django.shortcuts import render, HttpResponseRedirect
from Users.models import User
from Users.forms import UserLoginForm, UserRegistrationForm, UserProfileForm
from django.contrib import auth
from django.urls import reverse
from django.contrib import messages
from Events.models import Event
from django.contrib.auth.decorators import login_required
# Create your views here.
def base(request):
    latest_events = Event.objects.order_by('-date')[:2]

    return render(request, 'Users/base.html', {'latest_events': latest_events})

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
        form = UserLoginForm()
    context = {'form': form}
    return render(request, 'Users/login.html', context)

def registration(request):
    if request.method == "POST":
        form = UserRegistrationForm(data=request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Аккаунт успешно создан! Теперь войдите.")
            return HttpResponseRedirect(reverse('Users:login'))
        else:
            messages.error(request, 'Чет не так')
    else:
        form = UserRegistrationForm()
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
            HttpResponseRedirect(reverse('Users:profile'))
        else:
            print(form.errors)
    else:
        form = UserProfileForm(instance=request.user)
    my_events = Event.objects.filter(creator=request.user)
    context = {
        'form': form,
        'my_events': my_events
    }
    return render(request, 'Users/profile.html', context)

def logout(request):
    auth.logout(request)
    return HttpResponseRedirect(reverse('base'))