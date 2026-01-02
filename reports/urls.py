from django.urls import path
from reports.views import *
from comments.views import add_comment


app_name = 'reports'


urlpatterns = [
    path('new/', create_report, name='new'),
    path('ajax/get-components/', get_components, name='ajax_get_components'),
    path('', report_list, name='report_list'),
    path('<int:report_pk>/', report_detail, name='report_detail'), # This path is now relative to a project
    # path('<int:report_pk>/comment/', add_comment, name='add_comment'),
    path('my_reports/', my_report_list, name='my_reports'),
]