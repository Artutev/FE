from django.urls import path
from Events import views

app_name = 'Events'

urlpatterns = [
    path('Event/', views.event_list, name='event_list'),
    path('create/', views.create_event, name='create_event'),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('<int:event_id>/delete/', views.delete_event, name='delete_event'),
]