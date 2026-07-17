from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import threading
import logging

logger = logging.getLogger(__name__)

def _send_email_thread(msg):
    from django.db import close_old_connections
    try:
        msg.send()
    except Exception as e:
        logger.error(f"Failed to send async email: {e}", exc_info=True)
    finally:
        close_old_connections()

def send_notification_email(*, notification_type, subject, context, to_emails, cc_emails=None):
    """
    Sends an HTML email using Gmail SMTP.
    
    Email routing rules:
    - to_emails: recipients (owner/assignee)
    - cc_emails: CC lists (collaborators + reporter)
    """
    if not settings.EMAIL_HOST_USER:
        print(f"SMTP EMAIL NOT CONFIGURED: To: {to_emails}, Subject: {subject}")
        return

    # Add default context variables
    context['subject'] = subject
    context['from_email'] = settings.DEFAULT_FROM_EMAIL

    # Find the appropriate template based on the notification type
    template_name = f"notifications/emails/{notification_type}.html"
    
    # Render the HTML content
    try:
        html_content = render_to_string(template_name, context)
    except Exception as e:
        # Fallback: try base_email, or plain text HTML if not present
        print(f"Email template {template_name} failed to render: {e}. Using fallback.")
        try:
            html_content = render_to_string("notifications/emails/base_email.html", context)
        except Exception:
            # Absolute fallback
            html_content = f"<h3>{subject}</h3><p>{context.get('message', '')}</p><p>Check details on Reportary dashboard.</p>"

    text_content = strip_tags(html_content)

    # Build the email message
    msg = EmailMultiAlternatives(
        subject=subject,
        body=text_content,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=to_emails,
        cc=cc_emails or []
    )
    msg.attach_alternative(html_content, "text/html")
    
    # Send email in a background thread to prevent blocking Gunicorn / causing timeouts
    thread = threading.Thread(target=_send_email_thread, args=(msg,))
    thread.daemon = True
    thread.start()
