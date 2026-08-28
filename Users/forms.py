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
        self.language = language if language in PLACEHOLDERS else 'ru'
        super().__init__(*args, **kwargs)
        lang = self.language
        self.error_messages['invalid_login'] = (
            'Неверное имя пользователя или пароль.'
            if lang == 'ru' else
            'Please enter a correct username and password.'
        )
        self.fields['username'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['username']
        })
        self.fields['username'].label = 'Имя пользователя' if lang == 'ru' else 'Username'
        self.fields['password'].label = 'Пароль' if lang == 'ru' else 'Password'
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
        self.language = language if language in PLACEHOLDERS else 'ru'
        super().__init__(*args, **kwargs)
        lang = self.language
        self.fields['username'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['name']
        })
        self.fields['username'].label = 'Имя пользователя' if lang == 'ru' else 'Username'
        self.fields['email'].label = 'Электронная почта' if lang == 'ru' else 'Email'
        self.fields['email'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['email']
        })
        self.fields['birthDate'].label = 'Дата рождения' if lang == 'ru' else 'Birth date'
        self.fields['password1'].label = 'Пароль' if lang == 'ru' else 'Password'
        self.fields['password2'].label = 'Подтверждение пароля' if lang == 'ru' else 'Confirm password'
        self.fields['birthDate'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['birthDate']
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['password1']
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['password2']
        })

    def full_clean(self):
        super().full_clean()
        if self.language == 'en':
            translations = {
                'Обязательное поле.': 'This field is required.',
                'Пользователь с таким именем уже существует.': 'A user with that username already exists.',
                'Введите корректный адрес электронной почты.': 'Enter a valid email address.',
                'Введите правильный адрес электронной почты.': 'Enter a valid email address.',
                'Введённый пароль слишком короткий. Он должен содержать как минимум 8 символов.': 'This password is too short. It must contain at least 8 characters.',
                'Введённый пароль слишком короткий. Он должен содержать как минимум %(min_length)d символов.': 'This password is too short. It must contain at least %(min_length)d characters.',
                'Введённый пароль слишком широко распространён.': 'This password is too common.',
                'Введённый пароль состоит только из цифр.': 'This password is entirely numeric.',
                'Введенные пароли не совпадают.': "The two password fields didn't match.",
            }
            for field_name, errors in self._errors.items():
                for index, error in enumerate(errors.as_data()):
                    message = str(error.message)
                    if message in translations:
                        translated = translations[message]
                        if error.params:
                            translated = translated % error.params
                        errors[index] = translated


class UserProfileForm(UserChangeForm):
    username = forms.CharField(widget=forms.TextInput())
    email = forms.CharField(widget=forms.EmailInput(attrs={'readonly': True}))
    birthDate = forms.DateField(widget=forms.DateInput(attrs={'readonly': True}))
    class Meta:
        model = User
        fields = ('username', 'email', 'birthDate', 'is_profile_private')