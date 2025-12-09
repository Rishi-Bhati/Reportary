from django.urls import path
from . import views

# This is the app namespace. It helps Django distinguish the URL names of this app from other apps.
# For example, we can now use 'comments:add_comment' to refer to the URL pattern below.
app_name = 'comments'

urlpatterns = [
    # This URL is for adding a comment to a report.
    # It takes the report's primary key (report_pk) as a parameter.
    # The view function 'add_comment' in views.py will handle the request.
    # The name 'add_comment' is used to reverse the URL in templates.
    path('<int:report_pk>/add_comment/', views.add_comment, name='add_comment'),
]
