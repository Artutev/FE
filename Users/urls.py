from django.urls import path
from Users.views import login, registration, profile, logout
from Events.views import Event


app_name = 'Users'
urlpatterns = [
    path('Login/', login, name='login'),
    path('Registration/', registration, name='registration'),
    path('Profile/',profile, name='profile'),
    path('Logout/', logout, name='logout'),
]