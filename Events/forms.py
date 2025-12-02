from django import forms
from django import forms
from Events.models import Event

class EventForm(forms.ModelForm):
    date = forms.DateField(
        widget=forms.DateInput(
            attrs={'type': 'date', 'class': 'form-control'}
        ),
        input_formats=['%Y-%m-%d']
    )

    time = forms.TimeField(
        widget=forms.TimeInput(
            attrs={'type': 'time', 'class': 'form-control'}
        ),
        input_formats=['%H:%M']
    )

    class Meta:
        model = Event
        fields = ['name', 'event_type', 'date', 'time', 'location', 'description']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название'
            }),
            'event_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите место проведения'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Введите описание'
            }),
        }

