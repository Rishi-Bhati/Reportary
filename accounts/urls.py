from django.urls import path
from . import views

urlpatterns = [
    # The main page that holds the flow
    path('onboarding/', views.onboarding_home, name='onboarding_home'),
    
    # The HTMX partials
    path('onboarding/choice/', views.onboarding_choice, name='onboarding_choice'),
    path('onboarding/form/user/', views.onboarding_user_form, name='onboarding_user_form'),
    path('onboarding/form/org/', views.onboarding_org_form, name='onboarding_org_form'),
]