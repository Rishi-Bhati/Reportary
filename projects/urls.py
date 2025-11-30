from django.urls import path
from django.urls import include
from projects.views import register_project

urlpatterns = [
    path('', register_project, name='register_project'),
]