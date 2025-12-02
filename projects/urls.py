from django.urls import path
from django.urls import include
from projects.views import register_project, projects_view, project_detail, edit_project

urlpatterns = [
    path('register_project/', register_project, name='register_project'),
    path('', projects_view, name='projects_view'),
    path('project_detail/<int:pk>/',  project_detail, name='project_detail'),
    path('edit_project/<int:pk>/',  edit_project, name='edit_project'),
]