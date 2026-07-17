"""
public_portal/services.py

Business logic for:
- Creating / regenerating / toggling PublicReportingLinks
- Rate limiting anonymous submissions (pure Django ORM, no Redis needed)
- GDPR-safe IP hashing
"""
import hashlib
from datetime import timedelta
from django.utils import timezone
from django.conf import settings


# ─── IP Hashing ───────────────────────────────────────────────────────────────

def hash_ip(request) -> str:
    """
    Return a salted daily hash of the requester's IP.
    Raw IP is never retained — this satisfies GDPR.
    The hash rotates every calendar day automatically.
    """
    ip = _get_client_ip(request)
    today = timezone.now().date().isoformat()
    salt = settings.SECRET_KEY[:16]
    raw = f"{ip}:{today}:{salt}"
    return hashlib.sha256(raw.encode()).hexdigest()


def _get_client_ip(request) -> str:
    """Extract the real client IP.

    C-07: Use the RIGHTMOST IP from X-Forwarded-For — that's the one added
    by the trusted reverse proxy (e.g. Nginx/Render). The leftmost entry is
    client-controlled and can be trivially spoofed to bypass rate limiting.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Rightmost entry = trusted proxy hop; leftmost = client-supplied (untrusted)
        return x_forwarded_for.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '0.0.0.0')


# ─── Rate Limiting ────────────────────────────────────────────────────────────

def check_rate_limit(link, ip_hash: str) -> tuple[bool, int | None]:
    """
    Returns (allowed, retry_after_seconds).
    Checks both hourly and daily caps from settings.
    """
    from public_portal.models import AnonSubmission

    per_hour = getattr(settings, 'PUBLIC_PORTAL_RATE_LIMIT_PER_HOUR', 5)
    per_day  = getattr(settings, 'PUBLIC_PORTAL_RATE_LIMIT_PER_DAY', 20)

    now = timezone.now()
    hour_window_start = now - timedelta(hours=1)
    day_window_start  = now - timedelta(hours=24)

    hourly_count = AnonSubmission.objects.filter(
        link=link, ip_hash=ip_hash, submitted_at__gte=hour_window_start
    ).count()
    if hourly_count >= per_hour:
        # Tell client when the oldest submission in window expires
        oldest = AnonSubmission.objects.filter(
            link=link, ip_hash=ip_hash, submitted_at__gte=hour_window_start
        ).order_by('submitted_at').first()
        retry_after = int((oldest.submitted_at + timedelta(hours=1) - now).total_seconds()) + 1
        return False, max(retry_after, 60)

    daily_count = AnonSubmission.objects.filter(
        link=link, ip_hash=ip_hash, submitted_at__gte=day_window_start
    ).count()
    if daily_count >= per_day:
        oldest = AnonSubmission.objects.filter(
            link=link, ip_hash=ip_hash, submitted_at__gte=day_window_start
        ).order_by('submitted_at').first()
        retry_after = int((oldest.submitted_at + timedelta(hours=24) - now).total_seconds()) + 1
        return False, max(retry_after, 300)

    return True, None


# ─── Link Management ──────────────────────────────────────────────────────────

def get_or_create_link(project):
    """
    Return the existing PublicReportingLink for a project, or create one.
    Idempotent — safe to call multiple times.
    """
    from public_portal.models import PublicReportingLink
    link, _ = PublicReportingLink.objects.get_or_create(project=project)
    return link


def regenerate_link(project, actor):
    """
    Atomically issue a new token for the project's public link.
    Logs the action. Old token is immediately invalid.
    """
    from audit.services import log_action
    link = get_or_create_link(project)
    old_token = link.token
    link.regenerate()
    log_action(
        actor=actor,
        action='update',
        entity_type='PublicReportingLink',
        entity_id=link.pk,
        parent_type='Project',
        parent_id=project.id,
        field_name='token',
        old_value=old_token[:8] + '…',
        new_value=link.token[:8] + '…',
    )
    return link


def disable_link(project, actor):
    from audit.services import log_action
    link = get_or_create_link(project)
    if link.is_active:
        link.is_active = False
        link.save(update_fields=['is_active'])
        log_action(
            actor=actor, action='update', entity_type='PublicReportingLink',
            entity_id=link.pk, parent_type='Project', parent_id=project.id,
            field_name='is_active', old_value=True, new_value=False
        )
    return link


def enable_link(project, actor):
    from audit.services import log_action
    link = get_or_create_link(project)
    if not link.is_active:
        link.is_active = True
        link.save(update_fields=['is_active'])
        log_action(
            actor=actor, action='update', entity_type='PublicReportingLink',
            entity_id=link.pk, parent_type='Project', parent_id=project.id,
            field_name='is_active', old_value=False, new_value=True
        )
    return link


def toggle_link_anon(link, actor):
    """Toggle per-link anonymous submission allowance."""
    from audit.services import log_action
    old = link.allow_anonymous
    link.allow_anonymous = not old
    link.save(update_fields=['allow_anonymous'])
    log_action(
        actor=actor, action='update', entity_type='PublicReportingLink',
        entity_id=link.pk, parent_type='Project', parent_id=link.project.id,
        field_name='allow_anonymous', old_value=old, new_value=link.allow_anonymous
    )
    return link


# ─── Policy Checks ────────────────────────────────────────────────────────────

def anon_reporting_allowed(project) -> tuple[bool, str]:
    """
    Hierarchical policy check:
      org policy → project policy
    Returns (allowed, reason).
    """
    # 1. Organisation-level gate (highest priority)
    if project.org and not project.org.anon_reporting_enabled:
        return False, "Anonymous reporting has been disabled by your organisation."

    # 2. Project-level gate
    if not project.anon_reporting_enabled:
        return False, "Anonymous reporting is disabled for this project."

    return True, ""
