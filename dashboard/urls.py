from django.urls import path
from dashboard.views import home
from django.urls import include

urlpatterns = [
    path('', home, name='home'),
    path('projects/', include('projects.urls')),
]
