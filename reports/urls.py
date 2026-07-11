from django.urls import path
from reports.views import *
from comments.views import add_comment


app_name = 'reports'


urlpatterns = [
    path('new/', create_report, name='new'),
    path('ajax/get-components/', get_components, name='ajax_get_components'),
    path('ajax/get-project-config/', get_project_config, name='ajax_get_project_config'),
    path('', report_list, name='report_list'),
    path('<uuid:report_uuid>/', report_detail, name='report_detail'),
    path('<uuid:report_uuid>/reassign/', reassign_report, name='reassign_report'),
    path('<uuid:report_uuid>/status/', change_report_status, name='change_report_status'),
    path('<uuid:report_uuid>/visibility/', change_report_visibility, name='change_report_visibility'),
    path('<uuid:report_uuid>/impact/', change_report_impact, name='change_report_impact'),
    path('<uuid:report_uuid>/edit/', edit_report, name='edit_report'),
    path('<uuid:report_uuid>/delete/', delete_report, name='delete_report'),
    path('<uuid:report_uuid>/bookmark/', toggle_bookmark, name='toggle_bookmark'),
    path('<uuid:report_uuid>/watch/', toggle_watch, name='toggle_watch'),
    path('ajax/check-duplicate/', ajax_check_duplicate, name='ajax_check_duplicate'),
    path('bookmarks-and-watches/', bookmarks_and_watches, name='bookmarks_and_watches'),
    path('save-search/', save_search, name='save_search'),
    path('saved-searches/<int:search_id>/delete/', delete_saved_search, name='delete_saved_search'),
    path('attachments/<int:attachment_id>/delete/', delete_attachment, name='delete_attachment'),
    path('my_reports/', my_report_list, name='my_reports'),
    # URL pattern for showing reports assigned to logged in user
    path('assigned_to_me/', assigned_to_me, name='assigned_to_me'),
    path('needs_attention/', needs_attention_view, name='needs_attention'),
]