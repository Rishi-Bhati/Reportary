from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.urls import reverse

def send_verification_email(request, user):
    """Sends a verification email with a secure token to the user."""
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    
    # Construct verification link
    verify_url = request.build_absolute_uri(
        reverse('accounts:verify_email', kwargs={'uidb64': uidb64, 'token': token})
    )
    
    context = {
        'username': user.username,
        'verify_url': verify_url,
        'message': "Verify your email to unlock reporting, commenting, project creation, and collaboration."
    }
    
    from notifications.email_service import send_notification_email
    send_notification_email(
        notification_type='verify_email',
        subject="Verify your Reportary email address",
        context=context,
        to_emails=[user.email]
    )

def send_welcome_email(request, user):
    """Sends a welcome email to the user after successful email verification."""
    display_name = user.username.split('@')[0] if '@' in user.username else user.username
    context = {
        'username': display_name,
        'message': "Welcome to Reportary! Your email has been verified. You can now create projects, file reports, collaborate with others, and manage your organisations."
    }
    
    from notifications.email_service import send_notification_email
    send_notification_email(
        notification_type='welcome',
        subject="Welcome to Reportary!",
        context=context,
        to_emails=[user.email]
    )
