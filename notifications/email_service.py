import json
import logging
import threading

import requests
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


# ─── Internal thread target ───────────────────────────────────────────────────
def _send_via_api(subject: str, html_body: str, to_emails: list, cc_emails: list):
    """
    Fires a single POST request to the mail API service.
    Runs inside a background daemon thread — only plain Python types are accepted.
    """
    api_key = settings.MAIL_API_KEY
    endpoint = settings.MAIL_API_ENDPOINT

    if not api_key:
        logger.warning("MAIL_API_KEY is not configured — skipping email dispatch.")
        return

    payload = {
        "to": ", ".join(to_emails),
        "subject": subject,
        "body": html_body,
    }
    if cc_emails:
        payload["cc"] = ", ".join(cc_emails)

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(
            endpoint,
            headers=headers,
            data=json.dumps(payload),
            timeout=15,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Failed to deliver email via API in background thread")


def send_notification_email(*, notification_type, subject, context, to_emails, cc_emails=None):
    """
    Renders an HTML email template and dispatches it asynchronously via the
    HTTP mail API (replaces SMTP).

    Email routing:
    - to_emails: primary recipients (owner / assignee)
    - cc_emails: CC list (collaborators + reporter)
    """
    # Add default context variables needed by templates
    context["subject"] = subject

    template_name = f"notifications/emails/{notification_type}.html"

    # Render HTML — all template work happens on the request thread before spawning
    try:
        html_content = render_to_string(template_name, context)
    except Exception as e:
        logger.warning("Email template %s failed (%s) — falling back.", template_name, e)
        try:
            html_content = render_to_string("notifications/emails/base_email.html", context)
        except Exception:
            html_content = (
                f"<h3>{subject}</h3>"
                f"<p>{context.get('message', '')}</p>"
                f"<p>Check details on your Reportary dashboard.</p>"
            )

    # Resolve recipients to plain lists of strings before entering the thread
    to_list = list(to_emails) if to_emails else []
    cc_list = list(cc_emails) if cc_emails else []

    thread = threading.Thread(
        target=_send_via_api,
        args=(subject, html_content, to_list, cc_list),
    )
    thread.daemon = True
    thread.start()


# ─── Legacy SMTP implementation (kept for future reference) ───────────────────
#
# from django.core.mail import EmailMultiAlternatives
# from django.utils.html import strip_tags
#
# def _send_email_thread_smtp(subject, body, from_email, to_emails, cc_emails, html_content):
#     from django.core.mail import EmailMultiAlternatives
#     from django.db import close_old_connections
#     try:
#         msg = EmailMultiAlternatives(
#             subject=subject,
#             body=body,
#             from_email=from_email,
#             to=to_emails,
#             cc=cc_emails or []
#         )
#         if html_content:
#             msg.attach_alternative(html_content, "text/html")
#         msg.send()
#     except Exception:
#         logger.exception("Failed to send asynchronous notification email in background thread")
#     finally:
#         close_old_connections()
