from django.urls import path
from django.urls import include
from projects.views import *

app_name = 'projects'

urlpatterns = [
    path('new/', register_project, name='new'),
    path('', projects_view, name='projects_view'),
    path('<int:pk>/',  project_detail, name='project_detail'),
    path('edit_project/<int:pk>/',  edit_project, name='edit_project'),
    path('<int:project_pk>/reports/', include('reports.urls')),
    path('my_projects/', my_projects_view, name='my_projects'),
]