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
    path('<uuid:report_uuid>/add_comment/', views.add_comment, name='add_comment'),
    # This URL is for editing a comment. It handles both GET (to show the form) and POST (to save the changes).
    path('<uuid:report_uuid>/edit_comment/<uuid:comment_uuid>/', views.edit_comment, name='edit_comment'),
    # This URL is for canceling the edit of a comment. It returns the original comment content.
    path('<uuid:report_uuid>/cancel_edit_comment/<uuid:comment_uuid>/', views.cancel_edit_comment, name='cancel_edit_comment'),
    # This URL is for toggling the visibility of a comment. Only the project owner can do this.
    path('<uuid:report_uuid>/toggle_comment_visibility/<uuid:comment_uuid>/', views.toggle_comment_visibility, name='toggle_comment_visibility'),
    # This URL is for deleting a comment.
    path('<uuid:report_uuid>/delete_comment/<uuid:comment_uuid>/', views.delete_comment, name='delete_comment'),
]
