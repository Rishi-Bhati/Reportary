import json
import logging
import threading
import time
import uuid
import hmac
import hashlib

import requests
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


# ─── Internal thread target ───────────────────────────────────────────────────
def _send_via_api(subject: str, html_body: str, to_emails: list, cc_emails: list):
    """
    Fires a single POST request to the mail API service with HMAC-SHA256 signing.
    Runs inside a background daemon thread — only plain Python types are accepted.
    """
    api_key = settings.MAIL_API_KEY
    api_secret = settings.MAIL_API_SECRET
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

    try:
        # Use compact JSON representation (no spacing) to avoid signature mismatch
        body = json.dumps(payload, separators=(',', ':'))

        # Get UTC epoch timestamp
        timestamp = str(int(time.time()))

        # Generate a random UUID nonce
        nonce = str(uuid.uuid4())

        # Compute SHA-256 of the raw request body
        body_hash = hashlib.sha256(body.encode('utf-8')).hexdigest()

        # Build canonical message: timestamp + \n + nonce + \n + body_hash
        canonical_message = f"{timestamp}\n{nonce}\n{body_hash}"

        # Sign the canonical message using the API secret
        signature = hmac.new(
            api_secret.encode('utf-8'),
            canonical_message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {
            'X-API-Key': api_key,
            'X-Timestamp': timestamp,
            'X-Nonce': nonce,
            'X-Signature': signature,
            'Content-Type': 'application/json'
        }

        response = requests.post(
            endpoint,
            headers=headers,
            data=body,
            timeout=15,
        )
        response.raise_for_status()
    except Exception:
        logger.exception("Failed to deliver email via API in background thread")


def send_api_email(subject: str, html_body: str, to_emails: list, cc_emails: list = None):
    """
    Queues an email for background dispatch using the secure workers email API.
    """
    to_list = [e for e in (to_emails or []) if e]
    cc_list = [e for e in (cc_emails or []) if e]

    if not to_list:
        logger.warning("send_api_email skipped — to_list is empty.")
        return

    logger.debug("Queuing email → to=%s cc=%s", to_list, cc_list)

    thread = threading.Thread(
        target=_send_via_api,
        args=(subject, html_body, to_list, cc_list),
    )
    thread.daemon = True
    thread.start()


def send_notification_email(*, notification_type, subject, context, to_emails, cc_emails=None):
    """
    Renders an HTML email template and dispatches it asynchronously via the
    HTTP mail API (replaces SMTP).

    To protect user privacy, we send separate individual emails to each recipient
    (both primary and CC'd) so that no recipient can see any other recipient's email address.
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

    # Collect all unique recipients
    recipients = set()
    if to_emails:
        for email in to_emails:
            if email:
                recipients.add(email.strip())
    if cc_emails:
        for email in cc_emails:
            if email:
                recipients.add(email.strip())

    # Send individual concurrent email requests
    for email in recipients:
        send_api_email(subject, html_content, [email], cc_emails=None)


from django.core.mail.backends.base import BaseEmailBackend

class ApiEmailBackend(BaseEmailBackend):
    """
    Django email backend that routes all emails (e.g. password resets)
    through the HTTP workers email API in background threads.
    Forces individual delivery to avoid recipient address leakage.
    """
    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        for message in email_messages:
            html_body = None
            if hasattr(message, 'alternatives') and message.alternatives:
                for alt, mimetype in message.alternatives:
                    if mimetype == 'text/html':
                        html_body = alt
                        break
            if not html_body:
                html_body = f"<div style='font-family: sans-serif; white-space: pre-wrap; line-height: 1.6;'>{message.body}</div>"

            # Merge all recipients to enforce individual sends (no leakage)
            recipients = set()
            if message.to:
                for r in message.to:
                    if r:
                        recipients.add(r.strip())
            if message.cc:
                for r in message.cc:
                    if r:
                        recipients.add(r.strip())
            if message.bcc:
                for r in message.bcc:
                    if r:
                        recipients.add(r.strip())

            if not recipients:
                continue

            try:
                for recipient in recipients:
                    send_api_email(
                        subject=message.subject,
                        html_body=html_body,
                        to_emails=[recipient],
                        cc_emails=None
                    )
                sent_count += 1
            except Exception:
                logger.exception("Failed to send message via ApiEmailBackend")
                if not self.fail_silently:
                    raise

        return sent_count

