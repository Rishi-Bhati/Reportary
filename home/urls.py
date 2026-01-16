from django.urls import path, include
from . import views

# The 'app_name' was commented out. If it were active, all url names in this file would be namespaced,
# e.g., 'home:landing_page'. The 'NoReverseMatch' error for 'home' occurred because no URL
# was named 'home', and redirecting often uses URL names. The fix was to use a different,
# existing URL name like 'dashboard' or 'landing_page'.
# app_name = 'home'

urlpatterns = [
    # The main landing page for the website.
    path('', views.landing_page, name='landing_page'),

    # This includes URLs from the dashboard app. This was causing some issues before
    # as it was included here and in the project's root urls.py.
    # It has been left here as per the latest working version.
    # path('dashboard/', include('dashboard.urls')),
    
    # These URLs are for loading partial HTML fragments with HTMX.
    # They render the login and signup cards dynamically on the landing page.
    path('auth/card/login/', views.login_card, name='login_card'),
    path('auth/card/signup/', views.signup_card, name='signup_card'),
    
    # These URLs handle the form submissions for login and signup.
    path('auth/submit/login/', views.handle_login, name='handle_login'),
    path('auth/submit/signup/', views.handle_signup, name='handle_signup'),

    #profile page
    path('profile/', views.profile_page, name='profile'),
    
    # Under development / coming soon page
    path('nota/', views.nota_page, name='nota'),
]