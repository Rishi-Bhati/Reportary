from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.contrib import messages
import random

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
    The commented-out code shows a previous implementation detail where an authenticated user
    would be redirected to the dashboard. This logic is often handled by middleware or
    in the views that require authentication.
    """
    # if request.user.is_authenticated:
    #     return redirect('home')
    # if request.user.is_authenticated:
    #     return redirect('dashboard/')
    
    return render(request, "home/landing_page.html")

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
            return redirect('dashboard')
        else:
            messages.error(request, "Invalid password.")

    # If the login fails or if the request is not POST, redirect back to the landing page.
    return redirect('landing_page')

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
            messages.error(request, "Passwords do not match!")
            return redirect('landing_page')
        
        # Check if a user with this email already exists.
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists!")
            return redirect('landing_page')

        # Create the user.
        # Initialize username as email; user will set a display name/tag during onboarding.
        try:
            user = User.objects.create_user(username=email, email=email, password=password)
            login(request, user)
            return redirect('accounts:onboarding_home')
        except Exception as e:
            messages.error(request, "An error occurred during account creation.")
            
    # If signup fails or if the request is not POST, redirect back to the landing page.
    return redirect('landing_page')


def profile_page(request):
    """Renders the user's profile page."""
    user = request.user
    content = {
        'user': user,
    }
    return render(request, "home/profile.html", content)