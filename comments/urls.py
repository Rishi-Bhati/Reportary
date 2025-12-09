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
    # This URL is for editing a comment. It handles both GET (to show the form) and POST (to save the changes).
    path('<int:report_pk>/edit_comment/<int:comment_pk>/', views.edit_comment, name='edit_comment'),
    # This URL is for canceling the edit of a comment. It returns the original comment content.
    path('<int:report_pk>/cancel_edit_comment/<int:comment_pk>/', views.cancel_edit_comment, name='cancel_edit_comment'),
    # This URL is for toggling the visibility of a comment. Only the project owner can do this.
    path('<int:report_pk>/toggle_comment_visibility/<int:comment_pk>/', views.toggle_comment_visibility, name='toggle_comment_visibility'),
]
