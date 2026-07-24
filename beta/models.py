from django.db import models


class BetaFeature(models.Model):
    """
    Registry of all beta and graduated-to-stable features.
    To graduate a feature: set status = 'stable'.
    All users will then have access without any enrollment check.
    """
    STATUS_CHOICES = [
        ('beta', 'Beta'),
        ('stable', 'Stable'),
    ]

    slug = models.SlugField(
        unique=True,
        help_text="Unique identifier used in code, e.g. 'custom_report_forms'"
    )
    name = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='beta')
    # Set to False to hide from the enrollment UI (e.g. experimental/internal features)
    is_enrollable = models.BooleanField(
        default=True,
        help_text="If False, this feature is hidden from the beta enrollment UI."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"[{self.get_status_display()}] {self.name}"


class UserBetaEnrollment(models.Model):
    """
    Tracks a user's opt-in to the beta program.
    If 'features' is empty → user gets ALL enrollable beta features.
    If 'features' has specific entries → user gets only those features.
    """
    user = models.OneToOneField(
        'accounts.User',
        on_delete=models.CASCADE,
        related_name='beta_enrollment'
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    features = models.ManyToManyField(
        BetaFeature,
        blank=True,
        related_name='user_enrollments',
        help_text="Leave empty to enroll in ALL beta features."
    )

    def __str__(self):
        return f"{self.user.username} — beta enrolled"


class OrgBetaEnrollment(models.Model):
    """
    Tracks an organisation's opt-in to the beta program.
    Grants beta feature access to all projects under this org.
    Does NOT grant personal beta access to org members — they must enroll individually.
    """
    org = models.OneToOneField(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        related_name='beta_enrollment'
    )
    enrolled_by = models.ForeignKey(
        'accounts.User',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='org_beta_enrollments_created'
    )
    enrolled_at = models.DateTimeField(auto_now_add=True)
    features = models.ManyToManyField(
        BetaFeature,
        blank=True,
        related_name='org_enrollments',
        help_text="Leave empty to enroll in ALL beta features."
    )

    def __str__(self):
        return f"{self.org.name} — beta enrolled"
