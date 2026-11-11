from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    AuthenticationForm, PasswordResetForm, SetPasswordForm, UserChangeForm, UserCreationForm,
)
from django.core.cache import cache
from django.urls import reverse

from Users.backends import find_users
from Users.models import User
from Users.i18n import CS, tr
from Users.validators import PASSWORD_CHARS_MESSAGE

LOGIN_MAX_FAILURES = 10
LOGIN_LOCK_SECONDS = 15 * 60

# Стандартные сообщения Django (LANGUAGE_CODE = 'ru') → английский; чешский берётся из словаря CS.
ERROR_TRANSLATIONS = {
    'Обязательное поле.': 'This field is required.',
    'Пользователь с таким именем уже существует.': 'A user with that username already exists.',
    'Введите корректный адрес электронной почты.': 'Enter a valid email address.',
    'Введите правильный адрес электронной почты.': 'Enter a valid email address.',
    'Введённый пароль слишком короткий. Он должен содержать как минимум 8 символов.': 'This password is too short. It must contain at least 8 characters.',
    'Введённый пароль слишком короткий. Он должен содержать как минимум %(min_length)d символов.': 'This password is too short. It must contain at least %(min_length)d characters.',
    'Введённый пароль слишком широко распространён.': 'This password is too common.',
    'Введённый пароль состоит только из цифр.': 'This password is entirely numeric.',
    'Введенные пароли не совпадают.': "The two password fields didn't match.",
    'Введённый пароль слишком похож на %(verbose_name)s.': 'The password is too similar to the %(verbose_name)s.',
    PASSWORD_CHARS_MESSAGE: 'The password may only contain Latin letters, digits and symbols, without spaces.',
}


class TranslatedErrorsMixin:
    """Переводит стандартные ошибки Django на язык формы (self.language)."""

    def full_clean(self):
        super().full_clean()
        language = getattr(self, 'language', 'ru')
        if language == 'ru' or not self._errors:
            return
        for errors in self._errors.values():
            for index, error in enumerate(errors.as_data()):
                message = str(error.message)
                if message not in ERROR_TRANSLATIONS:
                    continue
                translated = tr(language, message, ERROR_TRANSLATIONS[message])
                if error.params:
                    try:
                        translated = translated % error.params
                    except (KeyError, TypeError, ValueError):
                        pass
                errors[index] = translated


def password_field(autocomplete):
    """Пароль не обрезается по краям (обычный CharField молча срезал бы пробелы)."""
    return forms.CharField(strip=False, widget=forms.PasswordInput(attrs={'autocomplete': autocomplete}))

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
PLACEHOLDERS['cs'] = {key: CS.get(value, value) for key, value in PLACEHOLDERS['en'].items()}

class UserLoginForm(AuthenticationForm):
    """Вход: имя без учёта регистра и пробелов по краям, понятные ошибки, лимит попыток."""
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'autocomplete': 'username', 'autocapitalize': 'none', 'spellcheck': 'false',
    }))
    password = password_field('current-password')

    class Meta:
        model = User
        fields = ('username', 'password')

    def __init__(self, *args, language='ru', **kwargs):
        kwargs.setdefault('label_suffix', '')
        self.language = language if language in PLACEHOLDERS else 'ru'
        self.unconfirmed_email = ''
        super().__init__(*args, **kwargs)
        lang = self.language
        self.error_messages = {
            **self.error_messages,
            'invalid_login': tr(lang, 'Неверное имя пользователя или пароль.',
                                'Please enter a correct username and password.'),
            'inactive': tr(lang, 'Email ещё не подтверждён. Введите код из письма, чтобы войти.',
                           'Your email is not confirmed yet. Enter the code from the email to sign in.'),
            'rate_limited': tr(lang, 'Слишком много попыток входа. Попробуйте через 15 минут.',
                               'Too many sign-in attempts. Try again in 15 minutes.'),
        }
        for name in ('username', 'password'):
            self.fields[name].error_messages['required'] = tr(lang, 'Обязательное поле.', 'This field is required.')
        self.fields['username'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['username']
        })
        self.fields['username'].label = tr(lang, 'Имя пользователя', 'Username')
        self.fields['password'].label = tr(lang, 'Пароль', 'Password')
        self.fields['password'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['password']
        })

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        if not username or password is None:
            return self.cleaned_data

        failures_key = f'login-failures:{username.lower()}'
        if cache.get(failures_key, 0) >= LOGIN_MAX_FAILURES:
            raise forms.ValidationError(self.error_messages['rate_limited'], code='rate_limited')

        self.user_cache = authenticate(self.request, username=username, password=password)
        if self.user_cache is not None:
            cache.delete(failures_key)
            return self.cleaned_data

        unconfirmed = next((
            user for user in find_users(username)
            if not user.is_active and user.check_password(password)
        ), None)
        if unconfirmed:
            self.unconfirmed_email = unconfirmed.email
            raise forms.ValidationError(self.error_messages['inactive'], code='inactive')

        cache.set(failures_key, cache.get(failures_key, 0) + 1, LOGIN_LOCK_SECONDS)
        raise forms.ValidationError(self.error_messages['invalid_login'], code='invalid_login')


class UserRegistrationForm(TranslatedErrorsMixin, UserCreationForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput(attrs={
        'autocomplete': 'username', 'autocapitalize': 'none', 'spellcheck': 'false',
    }))
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
    password1 = password_field('new-password')
    password2 = password_field('new-password')

    class Meta:
        model = User
        fields = ('username', 'email', 'birthDate', 'password1', 'password2')

    def __init__(self, *args, language='ru', **kwargs):
        kwargs.setdefault('label_suffix', '')
        self.language = language if language in PLACEHOLDERS else 'ru'
        super().__init__(*args, **kwargs)
        lang = self.language
        self.fields['username'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['name']
        })
        self.fields['username'].label = tr(lang, 'Имя пользователя', 'Username')
        self.fields['email'].label = tr(lang, 'Электронная почта', 'Email')
        self.fields['email'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['email']
        })
        self.fields['birthDate'].label = tr(lang, 'Дата рождения', 'Birth date')
        self.fields['password1'].label = tr(lang, 'Пароль', 'Password')
        self.fields['password2'].label = tr(lang, 'Подтверждение пароля', 'Confirm password')
        self.fields['birthDate'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['birthDate']
        })
        self.fields['password1'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['password1']
        })
        self.fields['password2'].widget.attrs.update({
            'placeholder': PLACEHOLDERS[lang]['password2']
        })

    def clean_username(self):
        # Занятость имени проверяем в clean(): там уже известен email (см. Users/signup.py)
        return self.cleaned_data.get('username', '')

    def clean(self):
        from Users import signup
        data = super().clean()
        username = data.get('username')
        email = (data.get('email') or '').strip()
        if email:
            data['email'] = email
        # Имя занято, даже если отличается только регистром («Anna» при живой «anna»).
        # Незавершённая регистрация (почта не подтверждена) имя не держит — см. signup.replaceable_signups.
        if username and signup.taken('username', username, email=email):
            self.add_error('username', forms.ValidationError(tr(
                self.language, 'Пользователь с таким именем уже существует.', 'A user with that username already exists.'
            ), code='unique'))
        if email and signup.taken('email', email):
            self.add_error('email', forms.ValidationError(tr(
                self.language,
                'Этот email уже зарегистрирован. Войдите или восстановите пароль.',
                'This email is already registered. Log in or reset your password.',
            ), code='unique'))
        return data

    def validate_unique(self):
        # Уникальность имени проверена в clean() с учётом незавершённых регистраций,
        # которые view удалит перед созданием нового аккаунта.
        self.instance.validate_unique(exclude=['username'])


class UserProfileForm(UserChangeForm):
    username = forms.CharField(max_length=150, widget=forms.TextInput())
    email = forms.CharField(widget=forms.EmailInput(attrs={'readonly': True}))
    birthDate = forms.DateField(widget=forms.DateInput(attrs={'readonly': True}))
    class Meta:
        model = User
        fields = ('username', 'email', 'birthDate', 'is_profile_private', 'email_notifications')

    def clean_username(self):
        username = self.cleaned_data.get('username', '')
        if User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует.', code='unique')
        return username


class EventTownPasswordResetForm(PasswordResetForm):
    """Сброс пароля: фирменное письмо на языке пользователя + не чаще раза в минуту на адрес."""

    def save(self, *args, **kwargs):
        email = self.cleaned_data.get('email', '').lower()
        cooldown_key = f'password-reset:{email}'
        if cache.get(cooldown_key):
            return
        cache.set(cooldown_key, True, 60)
        super().save(*args, **kwargs)

    def send_mail(self, subject_template_name, email_template_name, context, from_email, to_email,
                  html_email_template_name=None):
        from Users.emails import send_email, user_language

        user = context['user']
        path = reverse('Users:password_reset_confirm', kwargs={'uidb64': context['uid'], 'token': context['token']})
        send_email(
            to=to_email,
            template='password_reset',
            subject=('Сброс пароля в EventTown', 'Reset your EventTown password'),
            context={'user': user, 'reset_url': f"{context['protocol']}://{context['domain']}{path}"},
            language=user_language(user),
            fail_silently=True,
        )


class EventTownSetPasswordForm(TranslatedErrorsMixin, SetPasswordForm):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label_suffix', '')
        super().__init__(*args, **kwargs)
        self.language = getattr(self.user, 'language', '') or 'ru'
        for field in self.fields.values():
            field.widget.attrs.setdefault('autocomplete', 'new-password')
