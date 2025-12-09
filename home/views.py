from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.contrib import messages

User = get_user_model()

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

        # Since we use email for login, but Django's authenticate function uses 'username' by default,
        # we first fetch the user by their email to get their actual username.
        try:
            user_obj = User.objects.get(email=email)
            # Then we authenticate with the fetched username and the provided password.
            user = authenticate(username=user_obj.username, password=password)
            
            if user is not None:
                # If authentication is successful, log the user in.
                login(request, user)
                # The original code had redirect('home'), which caused a NoReverseMatch error
                # because there was no URL pattern named 'home'.
                # This was fixed by redirecting to 'dashboard' instead.
                return redirect('dashboard') # Go to Dashboard
            else:
                # If authentication fails (e.g., wrong password), show an error message.
                messages.error(request, "Invalid password.")
        except User.DoesNotExist:
            # If no user is found with the given email, show an error message.
            messages.error(request, "Account does not exist.")

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
        # We are setting the username to be the email initially.
        # The user will be prompted to choose a proper username during the onboarding process.
        try:
            user = User.objects.create_user(username=email, email=email, password=password)
            # Log the user in immediately after successful signup.
            login(request, user)
            # Redirect the new user to the onboarding page to complete their profile.
            return redirect('onboarding_home') # Go to Onboarding
        except Exception as e:
            messages.error(request, f"Error creating account: {e}")
            
    # If signup fails or if the request is not POST, redirect back to the landing page.
    return redirect('landing_page')