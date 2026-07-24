from django.urls import path
from beta import views

app_name = 'beta'

urlpatterns = [
    # User enrollment
    path('enroll/', views.enroll_user, name='enroll_user'),
    path('unenroll/', views.unenroll_user, name='unenroll_user'),

    # Org enrollment
    path('org/<uuid:org_uuid>/enroll/', views.enroll_org, name='enroll_org'),
    path('org/<uuid:org_uuid>/unenroll/', views.unenroll_org, name='unenroll_org'),
]
