from django.urls import path
from django.urls import include
from projects.views import *

app_name = 'projects'

urlpatterns = [
    path('new/', register_project, name='new'),
    path('', projects_view, name='projects_view'),
    path('<uuid:project_uuid>/',  project_detail, name='project_detail'),
    path('edit_project/<uuid:project_uuid>/',  edit_project, name='edit_project'),
    path('<uuid:project_uuid>/reports/', include('reports.urls')),
    path('my_projects/', my_projects_view, name='my_projects'),
    path('collaborating/', collaborating_projects_view, name='collaborating_projects'),
    
    # Task checklist routes
    path('<uuid:project_uuid>/tasks/add/', add_project_task, name='add_project_task'),
    path('<uuid:project_uuid>/tasks/<int:task_id>/toggle/', toggle_project_task, name='toggle_project_task'),
    path('<uuid:project_uuid>/tasks/<int:task_id>/delete/', delete_project_task, name='delete_project_task'),
]