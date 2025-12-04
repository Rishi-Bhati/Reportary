from django.urls import path
from dashboard.views import dashboard
from django.urls import include

urlpatterns = [
    path('', dashboard, name='dashboard'),
    # path('projects/', include('projects.urls')),
]
