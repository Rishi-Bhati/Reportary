from django.urls import path
from public_portal import views

app_name = 'public_portal'

urlpatterns = [
    # Public submission portal (no auth required)
    path('<str:token>/', views.portal_view, name='portal'),
    path('<str:token>/submitted/', views.portal_submitted, name='submitted'),
]
