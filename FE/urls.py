from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from Users.views import base, about
from Events.views import card_public, create_event


urlpatterns = [
    path('admin/', admin.site.urls),
    path('Users/', include('Users.urls', namespace='Users')),
    path('', base, name='base'),
    path('Event/', include('Events.urls', namespace='Events')),
    path('About/', about, name='about'),
    path('Chat/', include('Chat.urls', namespace='Chat')),
    path('i/<str:code>/', card_public, name='invite_card'),
]

if settings.DEBUG:
    # Locally Django serves uploads; in production nginx does
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
