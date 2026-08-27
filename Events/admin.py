from django.contrib import admin
from django import forms
from Events.models import Event, EventType

class EventAdminForm(forms.ModelForm):
	class Meta:
		model = Event
		fields = '__all__'

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		self.fields['event_type'].choices = EventType.localized_choices('ru')


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
	form = EventAdminForm


@admin.register(EventType)
class EventTypeAdmin(admin.ModelAdmin):
	list_display = ('code', 'name_ru', 'name_en', 'is_active', 'sort_order')
	list_filter = ('is_active',)
	search_fields = ('code', 'name_ru', 'name_en')
	ordering = ('sort_order', 'name_ru')
