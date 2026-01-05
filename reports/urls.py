from django.urls import path
from reports.views import *
from comments.views import add_comment


app_name = 'reports'


urlpatterns = [
    path('new/', create_report, name='new'),
    path('ajax/get-components/', get_components, name='ajax_get_components'),
    path('', report_list, name='report_list'),
    path('<int:report_pk>/', report_detail, name='report_detail'),
    path('<int:report_pk>/reassign/', reassign_report, name='reassign_report'),
    path('<int:report_pk>/status/', change_report_status, name='change_report_status'),
    path('<int:report_pk>/visibility/', change_report_visibility, name='change_report_visibility'),
    path('<int:report_pk>/impact/', change_report_impact, name='change_report_impact'),
    path('my_reports/', my_report_list, name='my_reports'),
    path('assigned_to_me/', assigned_to_me, name='assigned_to_me'),
]