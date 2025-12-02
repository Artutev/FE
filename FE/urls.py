from django.contrib import admin
from django.urls import path, include
from Users.views import base, about
from Events.views import create_event


urlpatterns = [
    path('admin/', admin.site.urls),
    path('Users/', include('Users.urls', namespace='Users')),
    path('', base, name='base'),
    path('Event/', include('Events.urls', namespace='Event')),
    path('About/', about, name='about'),

]
