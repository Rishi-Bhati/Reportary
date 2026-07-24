import secrets
from django.db import models
from django.utils import timezone


def generate_token():
    """Generate a cryptographically secure 48-byte URL-safe token (384-bit entropy)."""
    return secrets.token_urlsafe(48)


class PublicReportingLink(models.Model):
    """
    A unique public URL token tied to a project.
    Visiting /p/<token>/ opens the anonymous submission portal for that project.
    Only one active link per project exists at a time; regenerating replaces the token.
    """
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='public_link'
    )
    token = models.CharField(
        max_length=80,
        unique=True,
        db_index=True,
        default=generate_token
    )
    is_active = models.BooleanField(
        default=True,
        help_text="If False, visiting this link shows a disabled page."
    )
    allow_anonymous = models.BooleanField(
        default=True,
        help_text="Per-link toggle: allow unauthenticated users to submit via this link."
    )
    created_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='created_public_links'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    regenerated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"PublicLink for {self.project.title} ({'active' if self.is_active else 'disabled'})"

    def get_absolute_url(self):
        from django.urls import reverse
        return reverse('public_portal:portal', kwargs={'token': self.token})

    def regenerate(self):
        """Atomically replace the token and stamp regenerated_at."""
        self.token = generate_token()
        self.regenerated_at = timezone.now()
        self.save(update_fields=['token', 'regenerated_at'])


class AnonSubmission(models.Model):
    """
    Lightweight record of each anonymous submission — used only for rate limiting.
    The raw IP is NEVER stored; only a salted daily hash.
    """
    link = models.ForeignKey(
        PublicReportingLink,
        on_delete=models.CASCADE,
        related_name='anon_submissions'
    )
    # SHA-256(ip + date.isoformat() + SECRET_KEY[:16])  — rotates daily, GDPR-safe
    ip_hash = models.CharField(max_length=64, db_index=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    report = models.OneToOneField(
        'reports.Report',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='anon_submission_record'
    )

    class Meta:
        ordering = ['-submitted_at']

    def __str__(self):
        return f"AnonSubmission on {self.link} at {self.submitted_at}"


# ─── Beta Feature: Portal Custom Styling ─────────────────────────────────────
# Slug: 'portal_custom_styling'
# This model lives here in the public_portal app. Beta is just a gate.
# When this feature graduates to stable, it stays here — nothing needs to move.

class PortalTheme(models.Model):
    """
    Custom styling configuration for a project's public portal.
    Beta feature slug: 'portal_custom_styling'

    Two layers of styling:
    1. Structured fields → safe CSS custom properties (sanitized by field type)
    2. custom_css → arbitrary CSS, server-sanitized and scoped to #portal-wrapper

    When this feature graduates to stable, only BetaFeature.status changes.
    This model stays exactly here.
    """
    project = models.OneToOneField(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='portal_theme'
    )

    # ── Structured convenience fields (always safe, no injection risk) ────────
    primary_color = models.CharField(max_length=20, default='#6366f1')
    background_color = models.CharField(max_length=20, default='#0f0f1a')
    card_background = models.CharField(max_length=20, default='#1a1a2e')
    text_color = models.CharField(max_length=20, default='#e2e8f0')
    accent_color = models.CharField(max_length=20, default='#818cf8')
    font_family = models.CharField(
        max_length=100,
        default='Inter',
        help_text="Google Font name or CSS font stack."
    )
    border_radius = models.CharField(max_length=10, default='12px')

    # ── Arbitrary custom CSS (sanitized server-side before rendering) ─────────
    custom_css = models.TextField(
        blank=True,
        default='',
        help_text=(
            "Arbitrary CSS injected into the portal page. "
            "Server-sanitized and scoped to #portal-wrapper. "
            "Dangerous directives (script, javascript:, expression(), external @import) are stripped."
        )
    )

    # ── Optional branding overrides ───────────────────────────────────────────
    custom_logo_url = models.URLField(
        null=True, blank=True,
        help_text="URL to a logo image displayed on the portal."
    )
    custom_heading = models.CharField(
        max_length=200,
        null=True, blank=True,
        help_text="Custom heading text shown on the portal form."
    )

    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PortalTheme for {self.project.title}"

    def to_css_vars(self) -> str:
        """Render structured fields as CSS custom properties on :root."""
        return (
            f"--portal-primary: {self.primary_color};\n"
            f"--portal-bg: {self.background_color};\n"
            f"--portal-card-bg: {self.card_background};\n"
            f"--portal-text: {self.text_color};\n"
            f"--portal-accent: {self.accent_color};\n"
            f"--portal-radius: {self.border_radius};\n"
            f"--portal-font: '{self.font_family}', sans-serif;\n"
        )

