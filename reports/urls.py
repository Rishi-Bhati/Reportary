from django.urls import path
from django.urls import include
from reports.views import report_list, report_detail, create_report


app_name = 'reports'


urlpatterns = [
    path('', report_list, name='report_list'),
    path('<int:pk>/', report_detail, name='report_detail'),
    path('new/', create_report, name='new'),
]