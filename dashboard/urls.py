from django.urls import path
from dashboard.views import dashboard
from django.urls import include

# app_name = 'dashboard'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    # path('projects/', include('projects.urls')),
]
