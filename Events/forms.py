from django import forms
from django.utils import timezone
from Events.models import Event, EventType

PLACEHOLDERS = {
    'ru': {
        'name': 'Введите название',
        'event_type': 'Выберите тип события',
        'date': 'ДД.MM.ГГГГ',
        'time': 'ЧЧ:ММ',
        'location': 'Введите место проведения',
        'bride_name': 'Имя невесты (для свадеб)',
        'groom_name': 'Имя жениха (для свадеб)',
        'wedding_theme': 'Тема свадьбы (например, винтаж, рустик и т.п.)',
        'guest_count': 'Число гостей',
        'description': 'Введите описание',
    },
    'en': {
        'name': 'Enter the name',
        'event_type': 'Select event type',
        'date': 'DD.MM.YYYY',
        'time': 'HH:MM',
        'location': 'Enter the location',
        'bride_name': 'Bride name (for weddings)',
        'groom_name': 'Groom name (for weddings)',
        'wedding_theme': 'Wedding theme (e.g. vintage, rustic, etc.)',
        'guest_count': 'Number of guests',
        'description': 'Enter the description',
    },
}

LABELS = {
    'ru': {
        'name': 'Название',
        'event_type': 'Тип мероприятия',
        'date': 'Дата',
        'time': 'Время',
        'location': 'Место проведения',
        'is_private': 'Приватное мероприятие',
        'bride_name': 'Имя невесты',
        'groom_name': 'Имя жениха',
        'wedding_theme': 'Тема свадьбы',
        'guest_count': 'Ожидаемое количество гостей',
        'description': 'Описание',
    },
    'en': {
        'name': 'Name',
        'event_type': 'Event type',
        'date': 'Date',
        'time': 'Time',
        'location': 'Location',
        'is_private': 'Private event',
        'bride_name': 'Bride name',
        'groom_name': 'Groom name',
        'wedding_theme': 'Wedding theme',
        'guest_count': 'Expected guests',
        'description': 'Description',
    },
}

class EventForm(forms.ModelForm):
    date = forms.DateField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control date-picker-input',
                'autocomplete': 'off',
                'placeholder': PLACEHOLDERS['ru']['date'],
                'readonly': True,
            }
        ),
        input_formats=['%Y-%m-%d', '%d.%m.%Y']
    )

    time = forms.TimeField(
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': 'form-control time-picker-input',
                'autocomplete': 'off',
                'placeholder': PLACEHOLDERS['ru']['time'],
                'readonly': True,
            }
        ),
        input_formats=['%H:%M']
    )

    latitude = forms.FloatField(required=False, widget=forms.HiddenInput())
    longitude = forms.FloatField(required=False, widget=forms.HiddenInput())

    class Meta:
        model = Event
        fields = [
            'name',
            'event_type',
            'date',
            'time',
            'latitude',
            'longitude',
            'location',
            'is_private',
            'bride_name',
            'groom_name',
            'wedding_theme',
            'guest_count',
            'description'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['name']
            }),
            'event_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['location']
            }),
            'is_private': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'bride_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['bride_name']
            }),
            'groom_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['groom_name']
            }),
            'wedding_theme': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['wedding_theme']
            }),
            'guest_count': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': PLACEHOLDERS['ru']['guest_count']
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': PLACEHOLDERS['ru']['description']
            }),
        }

    def __init__(self, *args, language='ru', **kwargs):
        self.language = language if language in ('ru', 'en') else 'ru'
        super().__init__(*args, **kwargs)

        lang = self.language
        self.fields['name'].label = LABELS[lang]['name']
        self.fields['event_type'].label = LABELS[lang]['event_type']
        self.fields['date'].label = LABELS[lang]['date']
        self.fields['time'].label = LABELS[lang]['time']
        self.fields['location'].label = LABELS[lang]['location']
        self.fields['is_private'].label = LABELS[lang]['is_private']
        self.fields['bride_name'].label = LABELS[lang]['bride_name']
        self.fields['groom_name'].label = LABELS[lang]['groom_name']
        self.fields['wedding_theme'].label = LABELS[lang]['wedding_theme']
        self.fields['guest_count'].label = LABELS[lang]['guest_count']
        self.fields['description'].label = LABELS[lang]['description']

        self.fields['name'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['name']})
        self.fields['event_type'].choices = EventType.localized_choices(lang)
        self.fields['location'].required = False
        self.fields['description'].required = False
        self.fields['date'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['date']})
        self.fields['time'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['time']})
        self.fields['location'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['location']})
        self.fields['bride_name'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['bride_name']})
        self.fields['groom_name'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['groom_name']})
        self.fields['wedding_theme'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['wedding_theme']})
        self.fields['guest_count'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['guest_count']})
        self.fields['description'].widget.attrs.update({'placeholder': PLACEHOLDERS[lang]['description']})

    def clean(self):
        cleaned_data = super().clean()
        event_date = cleaned_data.get('date')
        event_time = cleaned_data.get('time')
        event_type = cleaned_data.get('event_type')
        location = cleaned_data.get('location')

        if event_type != 'other' and not location:
            message = (
                'Укажите место проведения.'
                if self.language == 'ru'
                else 'Please enter a location.'
            )
            self.add_error('location', message)

        if event_date and event_time:
            event_datetime = timezone.make_aware(
                timezone.datetime.combine(event_date, event_time),
                timezone.get_current_timezone()
            )
            if event_datetime < timezone.now():
                raise forms.ValidationError(
                    "Невозможно создать мероприятие в прошлом. Пожалуйста, выберите дату и время в будущем."
                )

        return cleaned_data

