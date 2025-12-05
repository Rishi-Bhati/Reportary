from django.urls import path
from django.urls import include
from reports.views import report_list, report_detail, create_report, get_components


app_name = 'reports'


urlpatterns = [
    path('new/', create_report, name='new'),
    path('ajax/get-components/', get_components, name='ajax_get_components'),
    path('', report_list, name='report_list'),
    path('<int:report_pk>/', report_detail, name='report_detail'), # This path is now relative to a project
]