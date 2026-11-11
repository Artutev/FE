from django.urls import path
from Events import views

app_name = 'Events'

urlpatterns = [
    path('', views.event_list, name='event_list'),
    path('archive/', views.event_archive, name='event_archive'),
    path('create/', views.create_event, name='create_event'),
    path('map-link/', views.map_link, name='map_link'),
    path('<int:event_id>/', views.event_detail, name='event_detail'),
    path('<int:event_id>/calendar.ics', views.event_calendar, name='event_calendar'),
    path('<int:event_id>/invitation/', views.download_invitation, name='download_invitation'),
    path('<int:event_id>/edit/', views.edit_event, name='edit_event'),
    path('<int:event_id>/delete/', views.delete_event, name='delete_event'),
    path('<int:event_id>/register/', views.register_event, name='register_event'),
    path('<int:event_id>/card/', views.card_editor, name='card_editor'),
    path('<int:event_id>/invite/', views.invite_friends, name='invite_friends'),
    path('<int:event_id>/unregister/', views.unregister_event, name='unregister_event'),
]