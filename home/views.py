from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.urls import reverse
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
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
    from django.utils.http import url_has_allowed_host_and_scheme
    next_url = request.GET.get('next')
    if request.user.is_authenticated:
        if next_url and url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            return redirect(next_url)
        return redirect('dashboard:dashboard')
    return render(request, "home/landing_page.html", {'next': next_url})

def changelog_view(request):
    """
    Renders the changelog/what's new page.
    """
    return render(request, "home/changelog.html")

def login_card(request):
    """Renders the HTMX partial for the login card."""
    next_url = request.GET.get('next')
    return render(request, "home/partials/login_card.html", {'next': next_url})

def signup_card(request):
    """Renders the HTMX partial for the signup card."""
    next_url = request.GET.get('next')
    return render(request, "home/partials/signup_card.html", {'next': next_url})

def handle_login(request):
    """
    Handles the user login form submission.
    """
    from django.utils.http import url_has_allowed_host_and_scheme
    if request.method == "POST":
        email = request.POST.get('email')
        password = request.POST.get('password')
        next_url = request.GET.get('next')

        # Validate next_url to prevent open redirect attacks
        if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = None

        # Authenticate using the email address.
        user = authenticate(request, username=email, password=password)
        
        if user is not None:
            login(request, user)
            response = HttpResponse(status=204)
            if next_url:
                response["HX-Redirect"] = next_url
            else:
                response["HX-Redirect"] = reverse("dashboard:dashboard")
            return response
        else:
            context = {
                'error': 'Invalid credentials. Please try again.',
                'next': next_url,
            }
            return render(request, "home/partials/login_card.html", context)

    # If the login fails or if the request is not POST, redirect back to the landing page.
    return redirect('home:landing_page')

def handle_signup(request):
    """
    Handles the user signup form submission.
    """
    from django.utils.http import url_has_allowed_host_and_scheme
    from django.core.validators import validate_email as django_validate_email
    from django.core.exceptions import ValidationError as DjangoValidationError
    if request.method == "POST":
        email = request.POST.get('email', '').strip()
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')
        next_url = request.GET.get('next')

        # Validate next_url to prevent open redirect
        if next_url and not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
            next_url = None

        # Validate email format server-side (M-09)
        try:
            django_validate_email(email)
        except DjangoValidationError:
            context = {'error': 'Please enter a valid email address.', 'next': next_url}
            return render(request, "home/partials/signup_card.html", context)

        # Basic validation for passwords.
        if password != confirm_password:
            context = {'error': 'Passwords do not match.', 'next': next_url}
            return render(request, "home/partials/signup_card.html", context)
        
        # Check if a user with this email already exists.
        if User.objects.filter(email=email).exists():
            context = {'error': 'Email already exists. Please try to log in.', 'next': next_url}
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
            context = {'error': errors, 'next': next_url}
            return render(request, "home/partials/signup_card.html", context)

        # Create the user.
        # Initialize username as email; user will set a display name/tag during onboarding.
        try:
            user = User.objects.create_user(username=email, email=email, password=password)
            user.is_email_verified = False
            user.save()

            # Trigger email verification email
            from accounts.email_utils import send_verification_email
            try:
                send_verification_email(request, user)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to send verification email: {e}")

            login(request, user)
            response = HttpResponse(status=204)
            if next_url:
                response["HX-Redirect"] = next_url
            else:
                response["HX-Redirect"] = reverse("accounts:onboarding_home")
            return response
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Signup error: {e}")
            context = {'error': 'An error occurred during account creation.', 'next': next_url}
            return render(request, "home/partials/signup_card.html", context)
            
    # If signup fails or if the request is not POST, redirect back to the landing page.
    return redirect('home:landing_page')


@login_required
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


def faq_page(request):
    """Renders the FAQ page."""
    faqs = [
        {
            "question": "What is Reportary?",
            "answer": "Reportary is a modern, collaborative bug and issue tracking platform designed for development teams. It helps you capture, organize, and resolve software issues efficiently.",
        },
        {
            "question": "Who can create a project?",
            "answer": "Any registered and email-verified user can create a project. Projects can be public (visible to anyone) or private (restricted to team members only).",
        },
        {
            "question": "How do I invite team members to my project?",
            "answer": "Open your project's dashboard and use the 'Invite Collaborator' option. Invited users will receive an in-app notification and can accept or decline the invitation.",
        },
        {
            "question": "What is the difference between Severity and Impact?",
            "answer": "Severity describes how technically bad the bug is (e.g., Critical, High, Medium, Low). Impact describes how many users or systems are affected. Both help prioritize issues effectively.",
        },
        {
            "question": "Can I make a report private?",
            "answer": "Yes. When creating or editing a report, you can toggle its visibility to private. Private reports are only visible to project members and the reporter.",
        },
        {
            "question": "What happens when I delete my account?",
            "answer": "Your account is deactivated immediately and permanently deleted after 30 days. During this window, you can reactivate it by logging back in. Your reports and project history are preserved.",
        },
        {
            "question": "Is my data secure?",
            "answer": "Yes. We use industry-standard encryption for all data in transit and at rest. Access to projects is strictly enforced via our permissions system — users can only access what they are explicitly authorized for.",
        },
        {
            "question": "How do I report a bug in Reportary itself?",
            "answer": "You can report bugs or request features directly on our tracking project. Just click <a href='/projects/019f2e92-7f0d-78e9-92b3-9431a1014882/reports/new/' class='text-[#226ce0] underline underline-offset-2'>here</a> to file a report.",
        },
        {
            "question": "Is Reportary free?",
            "answer": "Yes, Reportary is free during its current beta phase. We plan to introduce subscription tiers in the future, but the core functionality will always remain accessible.",
        },
        {
            "question": "How do I reset my password?",
            "answer": "Click 'Forgot Password' on the login page. You will receive an email with a secure link to set a new password.",
        },
    ]
    return render(request, "home/faq.html", {"faqs": faqs})


def privacy_page(request):
    """Renders the Privacy Policy page."""
    return render(request, "home/privacy.html")


def terms_page(request):
    """Renders the Terms of Service page."""
    return render(request, "home/terms.html")


def contact_page(request):
    """Renders and handles the Contact form with rate limiting (H-06)."""
    if request.method == "POST":
        # Rate limiting: 5 submissions per hour per IP using Django's cache
        from django.core.cache import cache
        client_ip = request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '0.0.0.0'))
        # Take rightmost IP from X-Forwarded-For to avoid spoofing
        client_ip = client_ip.split(',')[-1].strip()
        rate_key = f'contact_rate_{client_ip}'
        submission_count = cache.get(rate_key, 0)
        if submission_count >= 5:
            messages.error(request, "Too many messages sent. Please wait an hour before trying again.")
            return render(request, "home/contact.html", {})
        cache.set(rate_key, submission_count + 1, timeout=3600)  # 1-hour window
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message_body = request.POST.get("message", "").strip()

        if not all([name, email, subject, message_body]):
            messages.error(request, "Please fill in all fields.")
            return render(request, "home/contact.html", {
                "prefill": {"name": name, "email": email, "subject": subject, "message": message_body}
            })

        try:
            from django.core.mail import send_mail
            from django.conf import settings as django_settings
            import threading
            import logging
            
            logger = logging.getLogger(__name__)

            full_message = (
                f"Contact Form Submission\n"
                f"{'=' * 40}\n"
                f"From: {name} <{email}>\n"
                f"Subject: {subject}\n\n"
                f"{message_body}\n\n"
                f"{'=' * 40}\n"
                f"Sent via Reportary Contact Page"
            )
            
            def _send_contact_email():
                from django.db import close_old_connections
                try:
                    send_mail(
                        subject=f"[Reportary Contact] {subject}",
                        message=full_message,
                        from_email=django_settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[django_settings.CONTACT_EMAIL],
                        fail_silently=False,
                    )
                except Exception:
                    logger.exception("Failed to send contact email in background thread")
                finally:
                    close_old_connections()
                    
            thread = threading.Thread(target=_send_contact_email)
            thread.daemon = True
            thread.start()
            
            messages.success(request, "Your message has been received! We'll get back to you soon.")
            return redirect("home:contact")
        except Exception as e:
            messages.error(request, "Failed to submit form. Please try again later.")

    prefill = {}
    if request.user.is_authenticated:
        prefill["email"] = request.user.email
        prefill["name"] = request.user.name or request.user.username or ""

    return render(request, "home/contact.html", {"prefill": prefill})