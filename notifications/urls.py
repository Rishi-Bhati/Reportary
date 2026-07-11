from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_center, name='center'),
    path('<uuid:uuid>/toggle-read/', views.toggle_read, name='toggle_read'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('invite/<uuid:uuid>/accept/', views.accept_invite, name='accept_invite'),
    path('invite/<uuid:uuid>/decline/', views.decline_invite, name='decline_invite'),
]
