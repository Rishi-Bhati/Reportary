import secrets
import hashlib
from django.db import models
from uuid6 import uuid7


def generate_public_key():
    """Generate a short, human-readable public key (prefix + random hex)."""
    return 'rpk_' + secrets.token_hex(16)  # e.g. rpk_a3f2...


class ApiKey(models.Model):
    """
    A scoped public/secret key pair for programmatic API access.

    The secret key is NEVER stored in plaintext.
    It is shown to the user exactly once at creation time.
    Only a PBKDF2-SHA256 hash is persisted.
    """
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('revoked', 'Revoked'),
        ('expired', 'Expired'),
    ]

    uuid = models.UUIDField(default=uuid7, editable=False, unique=True, db_index=True)
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        related_name='api_keys'
    )
    name = models.CharField(max_length=100, help_text="User-given alias for this key")

    public_key = models.CharField(
        max_length=40,
        unique=True,
        db_index=True,
        default=generate_public_key
    )
    # PBKDF2-SHA256 hash of the secret key — plaintext is never stored
    hashed_secret = models.CharField(max_length=256)

    # Usage tracking
    last_used_at = models.DateTimeField(null=True, blank=True, db_index=True)
    last_used_ip = models.GenericIPAddressField(null=True, blank=True)

    # Lifecycle
    is_active = models.BooleanField(default=True, db_index=True)
    expires_at = models.DateTimeField(
        null=True, blank=True,
        help_text="Optional. Key auto-expires after this datetime."
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.public_key[:12]}...) — {self.user.username}"

    @staticmethod
    def hash_secret(raw_secret: str) -> str:
        """PBKDF2-SHA256 hash of the raw secret. Used at creation and verification."""
        import hashlib, os
        from django.conf import settings
        # Use Django's SECRET_KEY as salt pepper for extra hardening
        salt = hashlib.sha256(settings.SECRET_KEY.encode()).hexdigest()[:32]
        dk = hashlib.pbkdf2_hmac('sha256', raw_secret.encode(), salt.encode(), 260000)
        return dk.hex()

    def verify_secret(self, raw_secret: str) -> bool:
        """Constant-time comparison of submitted secret against stored hash."""
        expected = self.hash_secret(raw_secret)
        return secrets.compare_digest(self.hashed_secret, expected)

    @property
    def status(self):
        from django.utils import timezone
        if not self.is_active:
            return 'revoked'
        if self.expires_at and self.expires_at < timezone.now():
            return 'expired'
        return 'active'

    @property
    def is_usable(self) -> bool:
        return self.status == 'active'


class ApiKeyScope(models.Model):
    """
    Per-key, per-resource permission scopes.
    Not every key gets admin access — users choose exactly what each key can do.
    """
    RESOURCE_CHOICES = [
        ('reports', 'Reports'),
        ('comments', 'Comments'),
        ('projects', 'Projects'),
    ]
    ACTION_CHOICES = [
        ('read', 'Read'),
        ('create', 'Create'),
        ('delete', 'Delete'),
    ]

    api_key = models.ForeignKey(ApiKey, on_delete=models.CASCADE, related_name='scopes')
    resource = models.CharField(max_length=30, choices=RESOURCE_CHOICES)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)

    class Meta:
        unique_together = ('api_key', 'resource', 'action')

    def __str__(self):
        return f"{self.api_key.name}: {self.resource}.{self.action}"


class ApiRequestLog(models.Model):
    """
    Lightweight per-request usage log for metrics and auditing.
    Drives the usage metrics dashboard.
    """
    METHOD_CHOICES = [
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('PATCH', 'PATCH'),
        ('DELETE', 'DELETE'),
    ]

    api_key = models.ForeignKey(
        ApiKey,
        on_delete=models.CASCADE,
        related_name='request_logs',
        db_index=True,
    )
    method = models.CharField(max_length=10, choices=METHOD_CHOICES)
    endpoint = models.CharField(max_length=200)
    status_code = models.PositiveSmallIntegerField()
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    response_ms = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Response time in milliseconds"
    )
    requested_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ['-requested_at']
        indexes = [
            models.Index(fields=['api_key', 'requested_at']),
            models.Index(fields=['api_key', 'status_code']),
        ]

    def __str__(self):
        return f"{self.method} {self.endpoint} → {self.status_code} ({self.api_key.name})"
