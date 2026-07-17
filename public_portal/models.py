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
