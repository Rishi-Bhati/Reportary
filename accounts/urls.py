from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    # The main page that holds the flow
    path('onboarding/', views.onboarding_home, name='onboarding_home'),
    
    # The HTMX partials
    path('onboarding/choice/', views.onboarding_choice, name='onboarding_choice'),
    path('onboarding/form/user/', views.onboarding_user_form, name='onboarding_user_form'),
    path('onboarding/form/org/', views.onboarding_org_form, name='onboarding_org_form'),
    path('onboarding/form/dev/', views.onboarding_dev_form, name='onboarding_dev_form'),

    # User search for autocomplete
    path('user-search/', views.user_search, name='user_search'),

    # Edit profile
    path('profile/edit/', views.edit_profile, name='edit_profile'),

    # Email verification
    path('verify-email/<str:uidb64>/<str:token>/', views.verify_email, name='verify_email'),
    path('confirm-email-change/<str:uidb64>/<str:token>/<str:new_email_b64>/', views.confirm_email_change, name='confirm_email_change'),
    path('resend-verification/', views.resend_verification, name='resend_verification'),

    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='accounts/password_reset_form.html',
        email_template_name='notifications/emails/password_reset_email.txt',
        html_email_template_name='notifications/emails/password_reset_email.html',
        success_url='/accounts/password-reset/done/'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='accounts/password_reset_done.html'
    ), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='accounts/password_reset_confirm.html',
        success_url='/accounts/password-reset/complete/'
    ), name='password_reset_confirm'),
    path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(
        template_name='accounts/password_reset_complete.html'
    ), name='password_reset_complete'),
]