from django.urls import path
from django.urls import include
from projects.views import *
from public_portal import views as portal_views

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

    # Public portal management (owner-only HTMX endpoints)
    path('<uuid:project_uuid>/public-link/toggle/', portal_views.htmx_toggle_link, name='portal_toggle_link'),
    path('<uuid:project_uuid>/public-link/regenerate/', portal_views.htmx_regenerate_link, name='portal_regenerate_link'),
    path('<uuid:project_uuid>/public-link/toggle-anon/', portal_views.htmx_toggle_anon, name='portal_toggle_anon'),
    path('<uuid:project_uuid>/public-link/toggle-project-anon/', portal_views.htmx_toggle_project_anon, name='portal_toggle_project_anon'),
    path('<uuid:project_uuid>/public-link/toggle-anon-attachments/', portal_views.htmx_toggle_anon_attachments, name='portal_toggle_anon_attachments'),
]