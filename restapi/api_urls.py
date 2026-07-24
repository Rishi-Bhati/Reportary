from django.urls import path
from restapi import api_views

# REST API endpoint URLs — mounted at /api/v1/ in core/urls.py
app_name = 'api_v1'

urlpatterns = [
    path('reports/', api_views.reports_endpoint, name='reports'),
    path('reports/<uuid:report_uuid>/', api_views.report_detail_endpoint, name='report_detail'),
]
