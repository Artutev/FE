from django.urls import path
from django.contrib.auth import views as auth_views
from django.urls import reverse_lazy

from Users.forms import EventTownPasswordResetForm, EventTownSetPasswordForm
from Users.views import resend_confirmation, login, registration, profile, public_profile, logout, set_language, confirm_email, confirm_email_code, friends, send_friend_request, respond_friend_request, remove_friend


app_name = 'Users'
urlpatterns = [
    path('Login/', login, name='login'),
    path('Registration/', registration, name='registration'),
    path('Confirm/<uidb64>/<token>/', confirm_email, name='confirm_email'),
    path('Confirm-code/', confirm_email_code, name='confirm_email_code'),
    path('Confirm-code/resend/', resend_confirmation, name='resend_confirmation'),
    path('Password-reset/', auth_views.PasswordResetView.as_view(
        form_class=EventTownPasswordResetForm,
        template_name='Users/password_reset.html',
        success_url=reverse_lazy('Users:password_reset_done'),
    ), name='password_reset'),
    path('Password-reset/sent/', auth_views.PasswordResetDoneView.as_view(
        template_name='Users/password_reset_done.html',
    ), name='password_reset_done'),
    path('Password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        form_class=EventTownSetPasswordForm,
        template_name='Users/password_reset_confirm.html',
        success_url=reverse_lazy('Users:password_reset_complete'),
    ), name='password_reset_confirm'),
    path('Password-reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='Users/password_reset_complete.html',
    ), name='password_reset_complete'),
    path('Profile/', profile, name='profile'),
    path('User/<str:username>/', public_profile, name='public_profile'),
    path('Friends/', friends, name='friends'),
    path('Friends/add/<int:user_id>/', send_friend_request, name='send_friend_request'),
    path('Friends/respond/<int:request_id>/<str:action>/', respond_friend_request, name='respond_friend_request'),
    path('Friends/remove/<int:user_id>/', remove_friend, name='remove_friend'),
    path('Logout/', logout, name='logout'),
    path('Language/<str:lang_code>/', set_language, name='set_language'),
]