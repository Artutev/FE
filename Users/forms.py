from tkinter import image_types

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm, UserChangeForm

from Users.models import User

PLACEHOLDERS = {
    'ru': {
        'username': 'Имя пользователя',
        'password': 'Пароль',
        'email': 'Электронная почта',
        'name': 'Введите имя',
        'birthDate': 'ДД.MM.ГГГГ',
        'password1': 'Пароль',
        'password2': 'Подтверждение пароля',
    },
    'en': {
        'username': 'Username',
        'password': 'Password',
        'email': 'Email address',
        'name': 'Enter your name',
        'birthDate': 'DD.MM.YYYY',
        'password1': 'Password',
        'password2': 'Confirm password',
    },
}

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput())
    password = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ('username', 'password')

    def __init__(self, *args, language='ru', **kwargs):
        super().__init__(*args, **kwargs)
        lang = language if language in PLACEHOLDERS else 'ru'
        self.fields['username'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['username']
        })
        self.fields['password'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['password']
        })


class UserRegistrationForm(UserCreationForm):
    username = forms.CharField(widget=forms.TextInput())
    email = forms.CharField(widget=forms.EmailInput())
    birthDate = forms.DateField(
        widget=forms.TextInput(attrs={
            'class': 'form-control date-picker-input',
            'autocomplete': 'off',
            'placeholder': PLACEHOLDERS['ru']['birthDate'],
            'readonly': True,
        }),
        input_formats=['%d.%m.%Y', '%Y-%m-%d']
    )
    password1 = forms.CharField(widget=forms.PasswordInput())
    password2 = forms.CharField(widget=forms.PasswordInput())

    class Meta:
        model = User
        fields = ('username', 'email', 'birthDate', 'password1', 'password2')

    def __init__(self, *args, language='ru', **kwargs):
        super().__init__(*args, **kwargs)
        lang = language if language in PLACEHOLDERS else 'ru'
        self.fields['username'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['name']
        })
        self.fields['email'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['email']
        })
        self.fields['birthDate'].label = 'Дата рождения' if lang == 'ru' else 'Birth date'
        self.fields['birthDate'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['birthDate']
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['password1']
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['password2']
        })


class UserProfileForm(UserChangeForm):
    username = forms.CharField(widget=forms.TextInput())
    email = forms.CharField(widget=forms.EmailInput(attrs={'readonly': True}))
    birthDate = forms.DateField(widget=forms.DateInput(attrs={'readonly': True}))
    class Meta:
        model = User
        fields = ('username', 'email', 'birthDate', 'is_profile_private')