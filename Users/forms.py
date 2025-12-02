from tkinter import image_types

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm

from Users.models import User

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Имя пользователя'
    }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Пароль'
    }))
    class Meta:
        model = User
        fields = ('username', 'password')


class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Введите имя'
    }))
    email = forms.CharField(widget=forms.EmailInput(attrs={
        'placeholder': 'Электронная почта'
    }))
    birthDate = forms.DateField(widget=forms.DateInput(attrs={
        'type': 'date'
    }))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Пароль'
    }))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Подтверждение пароля'
    }))

    class Meta:
        model = User
        fields = ('username', 'email', 'birthDate', 'password1', 'password2')


class UserProfileForm(UserChangeForm):
    username = forms.CharField(widget=forms.TextInput())
    email = forms.CharField(widget=forms.EmailInput(attrs={'readonly': True}))
    birthDate = forms.DateField(widget=forms.DateInput(attrs={'readonly': True}))
    class Meta:
        model = User
        fields = ('username', 'email', 'birthDate')