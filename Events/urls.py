from django.urls import path
from Events import views

app_name = 'Events'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('archive/', views.event_archive, name='event_archive'),
    path('create/', views.create_event, name='create_event'),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('<int:event_id>/invitation/', views.download_invitation, name='download_invitation'),
    path('<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('<int:event_id>/register/', views.register_event, name='register_event'),
    path('<int:event_id>/unregister/', views.unregister_event, name='unregister_event'),
]