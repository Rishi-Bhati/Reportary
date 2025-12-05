from django.urls import path, include
from . import views

# app_name = 'home'

urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('dashboard/', include('dashboard.urls')),
    
    # HTMX Partials
    path('auth/card/login/', views.login_card, name='login_card'),
    path('auth/card/signup/', views.signup_card, name='signup_card'),
    
    # Form Actions (The "Lets Go" buttons)
    path('auth/submit/login/', views.handle_login, name='handle_login'),
    path('auth/submit/signup/', views.handle_signup, name='handle_signup'),
]