from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.contrib import messages
import random
import re

User = get_user_model()


def nota_page(request):
    """Renders the 'under development' page with random fun messages."""
    fun_messages = [
        # "This page doesn't exist. Much like your patience, apparently.",
        # "Congratulations! You found absolutely nothing. Proud of yourself?",
        "This feature is coming soon. And by 'soon' we mean 'when we feel like it'.",
        "The developer was too busy procrastinating to build this page.",
        "Error 404: Developer motivation not found.",
        # "You clicked expecting content? That's adorable.",
        "This page is as complete as the developer's sleep schedule. So, not at all.",
        "The developer promised this would be done 'by tomorrow'. That was three weeks ago.",
        "You're early. Or we're late. Definitely we're late.",
        "The backlog is longer than the developer's list of excuses. And that's saying something.",
        "The developer wrote 'TODO' here six months ago and never came back.",
        # "You expected a feature? In THIS economy? In THIS codebase?",
        "We could finish this page, or we could add another notification bell that doesn't work.",
        # Logout roasts
        # "Fun fact: This app doesn't even have a proper logout button. But sure, let's add more features.",
        "Want to logout? Good luck. The developer hasn't figured that out yet either.",
        "This page is missing. So is the logout button. We have priorities, clearly.",
        "The logout feature and this page have something in common: they don't exist.",
        # "You're stuck here forever. Just like you're stuck logged in. We don't do exits.",
    ]
    
    context = {
        'message': random.choice(fun_messages),
    }
    return render(request, "home/nota.html", context)

def landing_page(request):
    """
    Renders the main landing page.
    Redirects authenticated users to the dashboard.
    """
    if request.user.is_authenticated:
        return redirect('dashboard:dashboard')
    return render(request, "home/landing_page.html")

def changelog_view(request):
    """
    Renders the changelog/what's new page.
    """
    return render(request, "home/changelog.html")

def login_card(request):
    """Renders the HTMX partial for the login card."""
    return render(request, "home/partials/login_card.html")

def signup_card(request):
    """Renders the HTMX partial for the signup card."""
    return render(request, "home/partials/signup_card.html")

def handle_login(request):
    """
    Handles the user login form submission.
    """
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Authenticate using the email address.
        # Note: 'username' argument is the specific keyword argument for the backend, 
        # even though we are passing the email.
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("dashboard:dashboard")
            return response
        else:
            context = {'error': 'Invalid credentials. Please try again.'}
            return render(request, "home/partials/login_card.html", context)

    # If the login fails or if the request is not POST, redirect back to the landing page.
    return redirect('home:landing_page')

def handle_signup(request):
    """
    Handles the user signup form submission.
    """
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Basic validation for passwords.
        if password != confirm_password:
            context = {'error': 'Passwords do not match.'}
            return render(request, "home/partials/signup_card.html", context)
        
        # Check if a user with this email already exists.
        if User.objects.filter(email=email).exists():
            context = {'error': 'Email already exists. Please try to log in.'}
            return render(request, "home/partials/signup_card.html", context)

        # Validate password strength with custom rules and Django validators.
        errors = []

        # Custom rules: min 8 chars, at least one uppercase, one lowercase, one number, one special character
        if len(password) < 8:
            errors.append('Password must be at least 8 characters long.')
        if not re.search(r'[A-Z]', password):
            errors.append('Password must contain at least one uppercase letter.')
        if not re.search(r'[a-z]', password):
            errors.append('Password must contain at least one lowercase letter.')
        if not re.search(r'[0-9]', password):
            errors.append('Password must contain at least one number.')
        if not re.search(r'[!@#$%^&*()_\-+=\[\]{};:\'",.<>?/\\`~]', password):
            errors.append('Password must contain at least one special character (e.g. @, #, $, !, &).')

        # Also run Django's validators to catch common/weak passwords
        try:
            validate_password(password)
        except ValidationError as e:
            errors.extend(list(e.messages))

        if errors:
            context = {'error': errors}
            return render(request, "home/partials/signup_card.html", context)

        # Create the user.
        # Initialize username as email; user will set a display name/tag during onboarding.
        try:
            user = User.objects.create_user(username=email, email=email, password=password)
            login(request, user)
            response = HttpResponse(status=204)
            response["HX-Redirect"] = reverse("accounts:onboarding_home")
            return response
        except Exception:
            context = {'error': 'An error occurred during account creation.'}
            return render(request, "home/partials/signup_card.html", context)
            
    # If signup fails or if the request is not POST, redirect back to the landing page.
    return redirect('home:landing_page')


def profile_page(request):
    """Renders the user's profile page."""
    user = request.user
    owned_organisations = user.organisations.all()
    member_organisations = user.organisation_members.all()
    
    content = {
        'user': user,
        'owned_organisations': owned_organisations,
        'member_organisations': member_organisations,
    }
    return render(request, "home/profile.html", content)