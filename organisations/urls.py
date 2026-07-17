from django.urls import path
from . import views

app_name = 'organisations'

urlpatterns = [
    # List all user's organisations
    path('', views.organisation_list, name='list'),
    
    # Create new organisation
    path('create/', views.create_organisation, name='create'),
    
    # Main dashboard for an organisation
    path('<uuid:uuid>/', views.organisation_dashboard, name='dashboard'),
    
    # Organisation details (view/edit)
    path('<uuid:uuid>/details/', views.organisation_details, name='details'),
    
    # Toggle anonymous reporting policy
    path('<uuid:uuid>/toggle-anon/', views.organisation_toggle_anon, name='toggle_anon'),
    
    # Manage organisation members
    path('<uuid:uuid>/members/', views.organisation_members, name='members'),
    
    # View organisation projects
    path('<uuid:uuid>/projects/', views.organisation_projects, name='projects'),
    
    # Leave an organisation
    path('<uuid:uuid>/leave/', views.leave_organisation, name='leave'),
]
