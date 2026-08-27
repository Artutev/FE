from django.urls import path
from Users.views import login, registration, profile, public_profile, logout, set_language, confirm_email, confirm_email_code, friends, send_friend_request, respond_friend_request, remove_friend


app_name = 'Users'
urlpatterns = [
    path('Login/', login, name='login'),
    path('Registration/', registration, name='registration'),
    path('Confirm/<uidb64>/<token>/', confirm_email, name='confirm_email'),
    path('Confirm-code/', confirm_email_code, name='confirm_email_code'),
    path('Profile/', profile, name='profile'),
    path('User/<str:username>/', public_profile, name='public_profile'),
    path('Friends/', friends, name='friends'),
    path('Friends/add/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('Friends/respond/<int:request_id>/<str:action>/', respond_friend_request, name='respond_friend_request'),
    path('Friends/remove/<int:user_id>/', remove_friend, name='remove_friend'),
    path('Logout/', logout, name='logout'),
    path('Language/<str:lang_code>/', set_language, name='set_language'),
]