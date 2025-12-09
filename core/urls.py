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
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth.urls import views as auth_views
# from dashboard.views import home

urlpatterns = [
    # The Django admin interface
    path('admin/', admin.site.urls),
    
    # URLs for the landing page, login, and signup
    path('', include('home.urls')),
    
    # URLs for the main user dashboard
    path("dashboard/", include("dashboard.urls")),
    
    # URLs for account management, like onboarding
    path('accounts/', include('accounts.urls')),
    
    # URLs for project-related views. This is the main entry point for projects and their nested reports.
    path('projects/', include('projects.urls')),
    
    # The reports URLs are included within projects.urls, so this line was redundant and potentially problematic.
    # It's kept here but commented out to show the history of the chan/ges.
    path('reports/', include('reports.urls')),

    # URLs for the comments app.
    # We add a namespace 'comments' here.
    # This was the fix for the NoReverseMatch error, which occurred because Django couldn't find the namespaced URL 'comments:add_comment'.
    path('comments/', include('comments.urls', namespace='comments')),
]

# This is a standard practice for serving static files during development.
# In a production environment, a web server like Nginx or Apache should be configured to serve static files.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
