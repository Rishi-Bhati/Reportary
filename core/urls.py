"""
URL configuration for core project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import include
from django.conf.urls.i18n import i18n_patterns
import django.conf.urls.i18n as i18n_urls
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.urls import views as auth_views
# from dashboard.views import home
from core import views as core_views

urlpatterns = [
    # i18n language switching endpoint (POST /i18n/set_language/)
    path('i18n/', include('django.conf.urls.i18n')),

    # The Django admin interface
    path('admin/', admin.site.urls),
    # Global search
    path('search/', core_views.global_search, name='global_search'),
    path('search/glimpse/', core_views.global_search_glimpse, name='global_search_glimpse'),

    
    # URLs for the landing page, login, and signup
    path('', include('home.urls')),
    
    # URLs for the main user dashboard
    path("dashboard/", include("dashboard.urls")),
    
    # URLs for account management, like onboarding
    path('accounts/', include('accounts.urls')),

    # URLs for organisation management
    path('organisations/', include('organisations.urls')),

    # URLs for notification management
    path('notifications/', include('notifications.urls', namespace='notifications')),
    
    # URLs for project-related views.
    path('projects/', include('projects.urls')),
    
    path('reports/', include('reports.urls')),

    # Public reporting portal (no auth) — /p/<token>/
    path('p/', include('public_portal.urls', namespace='public_portal')),

    # URLs for the comments app.
    # We add a namespace 'comments' here.
    # This was the fix for the NoReverseMatch error, which occurred because Django couldn't find the namespaced URL 'comments:add_comment'.
    path('comments/', include('comments.urls', namespace='comments')),

    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
]

# This is a standard practice for serving static files during development.
# In a production environment, a web server like Nginx or Apache should be configured to serve static files.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
