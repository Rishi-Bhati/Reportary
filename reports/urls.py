from django.urls import path
from reports.views import *
from comments.views import add_comment


app_name = 'reports'


urlpatterns = [
    path('new/', create_report, name='new'),
    path('ajax/get-components/', get_components, name='ajax_get_components'),
    path('', report_list, name='report_list'),
    path('<uuid:report_uuid>/', report_detail, name='report_detail'),
    path('<uuid:report_uuid>/reassign/', reassign_report, name='reassign_report'),
    path('<uuid:report_uuid>/status/', change_report_status, name='change_report_status'),
    path('<uuid:report_uuid>/visibility/', change_report_visibility, name='change_report_visibility'),
    path('<uuid:report_uuid>/impact/', change_report_impact, name='change_report_impact'),
    path('my_reports/', my_report_list, name='my_reports'),
    path('assigned_to_me/', assigned_to_me, name='assigned_to_me'),
]