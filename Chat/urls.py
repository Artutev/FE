from django.urls import path

from Chat import views

app_name = 'Chat'
urlpatterns = [
    path('', views.chat_list, name='list'),
    path('<int:conversation_id>/', views.chat_detail, name='detail'),
    path('<int:conversation_id>/messages/', views.older_messages, name='older'),
    path('<int:conversation_id>/send/', views.send_message, name='send'),
    path('with/<str:username>/', views.start_direct, name='start_direct'),
    path('event/<int:event_id>/', views.event_chat, name='event'),
]
