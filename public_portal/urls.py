from django.urls import path
from public_portal import views

app_name = 'public_portal'

urlpatterns = [
    # Theme configuration (Beta feature)
    path('project/<uuid:project_uuid>/theme/', views.configure_portal_theme, name='configure_theme'),

    # Public submission portal (no auth required)
    path('<str:token>/', views.portal_view, name='portal'),
    path('<str:token>/submitted/', views.portal_submitted, name='submitted'),
]
