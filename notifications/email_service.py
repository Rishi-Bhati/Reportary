"""
Outbound email via the Unsent mail service (https://unsent.rishibhati.in).

Requests are authenticated with an HMAC-SHA256 signature over a canonical
message rather than a bearer token, so five headers must travel together:

    X-API-Key     the public key
    X-Timestamp   unix seconds, used for replay windows
    X-Nonce       32 hex chars, single-use
    X-Signature   "sha256=" + HMAC-SHA256(secret, canonical)
    Content-Type  application/json

where canonical is "<timestamp>\n<nonce>\n<sha256-hex-of-body>".

The signature covers the body *bytes actually sent*, so the payload is
serialised exactly once and those bytes are both hashed and posted. Re-encoding
between hashing and sending would break the signature.
"""
import hashlib
import hmac
import json
import logging
import secrets
import sys
import threading
import time

import requests
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT_SECONDS = 15


def dispatch_disabled() -> bool:
    """
    True when email must not actually leave the process.

    Django's test runner swaps the email backend, but this service bypasses that
    by posting over HTTP from a background thread — so it needs its own guard.
    Module-level (rather than inline) so tests can patch it.
    """
    return any('test' in arg for arg in sys.argv)


def build_signed_headers(body_bytes: bytes, api_key: str, api_secret: str,
                         timestamp: str = None, nonce: str = None) -> dict:
    """
    Build the five headers the mail service requires for `body_bytes`.

    Separated from the sender so the signing can be tested without network I/O —
    and so the hash is unambiguously taken over the bytes that get posted.
    `timestamp` and `nonce` are injectable for tests only; leave them unset in
    production so each request is unique.
    """
    timestamp = timestamp or str(int(time.time()))
    nonce = nonce or secrets.token_hex(16)

    body_hash = hashlib.sha256(body_bytes).hexdigest()
    canonical_message = f"{timestamp}\n{nonce}\n{body_hash}"
    signature = hmac.new(
        api_secret.encode('utf-8'),
        canonical_message.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    return {
        'Content-Type': 'application/json',
        'X-API-Key': api_key,
        'X-Timestamp': timestamp,
        'X-Nonce': nonce,
        # The service expects the algorithm prefix, not a bare hex digest.
        'X-Signature': f'sha256={signature}',
    }


def build_email_payload(subject: str, html_body: str, to_email: str) -> dict:
    """The request body the mail service accepts."""
    return {
        "to": to_email,
        "subject": subject,
        "html": html_body,
        "from_name": getattr(settings, 'MAIL_FROM_NAME', 'Reportary'),
    }


# ─── Internal thread target ───────────────────────────────────────────────────
def _send_via_api(subject: str, html_body: str, to_emails: list, cc_emails: list):
    """
    Fires a single POST request to the mail API service with HMAC-SHA256 signing.
    Runs inside a background daemon thread — only plain Python types are accepted.
    """
    if dispatch_disabled():
        return

    api_key = settings.MAIL_API_KEY
    api_secret = settings.MAIL_API_SECRET
    endpoint = settings.MAIL_API_ENDPOINT

    if not api_key or not api_secret:
        logger.warning("MAIL_API_KEY/MAIL_API_SECRET not configured — skipping email dispatch.")
        return

    # One recipient per request: callers fan out individually so no recipient
    # can see another's address. The service takes a single `to`.
    recipient = to_emails[0] if to_emails else None
    if not recipient:
        logger.warning("_send_via_api called with no recipient.")
        return

    try:
        payload = build_email_payload(subject, html_body, recipient)
        # Serialise once, to UTF-8 bytes. json.dumps produces a str, and passing
        # a str to requests lets httplib encode it as latin-1 — which raises on
        # any non-ASCII character, and this app sends Japanese email.
        body_bytes = json.dumps(payload, separators=(',', ':'), ensure_ascii=False).encode('utf-8')

        headers = build_signed_headers(body_bytes, api_key, api_secret)

        response = requests.post(
            endpoint,
            headers=headers,
            data=body_bytes,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        logger.debug("Email dispatched to %s (%s)", recipient, response.status_code)
    except requests.HTTPError as exc:
        body = getattr(exc.response, 'text', '')[:500]
        logger.error("Mail service rejected the request (%s): %s",
                     getattr(exc.response, 'status_code', '?'), body)
    except Exception:
        logger.exception("Failed to deliver email via API in background thread")


def send_api_email(subject: str, html_body: str, to_emails: list, cc_emails: list = None):
    """
    Queue an email for background dispatch via the mail service.

    One request per recipient. The service takes a single `to` and has no `cc`,
    which suits this app: recipients are fanned out individually so that no
    recipient can see another's address. Anything passed as `cc` is folded into
    that fan-out rather than dropped.
    """
    recipients = []
    for email in list(to_emails or []) + list(cc_emails or []):
        if email and email.strip() not in recipients:
            recipients.append(email.strip())

    if not recipients:
        logger.warning("send_api_email skipped — no recipients.")
        return

    logger.debug("Queuing email → %s recipient(s)", len(recipients))

    for recipient in recipients:
        thread = threading.Thread(
            target=_send_via_api,
            args=(subject, html_body, [recipient], None),
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

