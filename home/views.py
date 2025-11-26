from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth import get_user_model
from django.contrib import messages

User = get_user_model()

def landing_page(request):
    # if request.user.is_authenticated:
    #     return redirect('home')
    return render(request, "home/landing_page.html")

def login_card(request):
    return render(request, "home/partials/login_card.html")

def signup_card(request):
    return render(request, "home/partials/signup_card.html")

def handle_login(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')

        # Since we use Email to login, but Django expects Username by default,
        # we try to find the user by email first.
        try:
            user_obj = User.objects.get(email=email)
            user = authenticate(username=user_obj.username, password=password)
            
            if user is not None:
                login(request, user)
                return redirect('home') # Go to Dashboard
            else:
                messages.error(request, "Invalid password.")
        except User.DoesNotExist:
            messages.error(request, "Account does not exist.")

    # If failed, reload the page (or you could render the partial with errors)
    return redirect('landing_page')

def handle_signup(request):
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        if password != confirm_password:
            messages.error(request, "Passwords do not match!")
            return redirect('landing_page')
        
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already exists!")
            return redirect('landing_page')

        # Create the user
        # We set username=email initially. User changes this in Onboarding.
        try:
            user = User.objects.create_user(username=email, email=email, password=password)
            login(request, user)
            return redirect('onboarding_home') # Go to Onboarding
        except Exception as e:
            messages.error(request, f"Error creating account: {e}")
            
    return redirect('landing_page')