from django.urls import path
from dashboard.views import dashboard, dashboard_overview, dashboard_analytics

app_name = 'dashboard'

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('overview/', dashboard_overview, name='overview'),
    path('analytics/', dashboard_analytics, name='analytics'),
]
