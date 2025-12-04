from django.urls import path
from django.urls import include
from projects.views import register_project, projects_view, project_detail, edit_project

app_name = 'projects'

urlpatterns = [
    path('new/', register_project, name='new'),
    path('', projects_view, name='projects_view'),
    path('<int:pk>/',  project_detail, name='project_detail'),
    path('edit_project/<int:pk>/',  edit_project, name='edit_project'),
    # path('<int:pk>/reports/', include('reports.urls')),
    path('<int:pk>/reports/', include('reports.urls')),
]