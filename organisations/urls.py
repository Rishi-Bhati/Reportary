from django.urls import path
from . import views

app_name = 'organisations'

urlpatterns = [
    path('leave/<uuid:uuid>/', views.leave_organisation, name='leave'),
]
