from django.urls import path
from restapi import api_views, dashboard_views

app_name = 'restapi'

# ─── Dashboard URLs (HTML) ────────────────────────────────────────────────────
urlpatterns = [
    path('dashboard/', dashboard_views.user_dashboard, name='dashboard'),
    path('dashboard/keys/create/', dashboard_views.create_key, name='create_key'),
    path('dashboard/keys/<uuid:key_uuid>/', dashboard_views.key_detail, name='key_detail'),
    path('dashboard/keys/<uuid:key_uuid>/revoke/', dashboard_views.revoke_key, name='revoke_key'),
    path('dashboard/keys/<uuid:key_uuid>/delete/', dashboard_views.delete_key, name='delete_key'),
    path('dashboard/org/<uuid:org_uuid>/', dashboard_views.org_dashboard, name='org_dashboard'),
]
