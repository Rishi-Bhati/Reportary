from django.db import models
from components.models import Component
from uuid6 import uuid7

# Create your models here.

class Project(models.Model):

    #UUID Field
    uuid = models.UUIDField(
    default=uuid7,
    editable=False,
    unique=True,
    db_index=True,
    # null=True,
    # blank=True,
    )

    owner = models.ForeignKey('accounts.User', on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    link = models.URLField(max_length=200)
    description = models.TextField()
    org = models.ForeignKey('organisations.Organisation', on_delete=models.SET_NULL, null=True, blank=True)
    project_head = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='managed_projects')
    VISIBILITY_CHOICES = [
        ('public', 'Public'),
        ('org', 'Organization Members Only'),
        ('private', 'Private (Owner & Collaborators Only)'),
    ]
    visibility = models.CharField(max_length=20, choices=VISIBILITY_CHOICES, default='public')
    public = models.BooleanField(default=True)
    collaborators = models.ManyToManyField('accounts.User', related_name='collaborations')
    
    max_attachments = models.PositiveIntegerField(default=5)
    allowed_attachment_types = models.CharField(max_length=255, default=".jpg,.jpeg,.png,.pdf,.doc,.docx,.xls,.xlsx,.zip,.txt")

    # Public Portal settings
    public_reporting_enabled = models.BooleanField(
        default=True,
        help_text="Allow this project to receive reports via its public reporting link."
    )
    anon_reporting_enabled = models.BooleanField(
        default=True,
        help_text="Allow anonymous (unauthenticated) users to submit reports via the public link."
    )
    anon_attachments_enabled = models.BooleanField(
        default=False,
        help_text="Allow anonymous reporters to attach files. Disabled by default to prevent abuse."
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
    @property
    def components(self):
        """Get all components related to this project"""
        return self.project_components.all()

    def get_project_members(self) -> set:
        """Returns the set of unique users who are members of this project (owner, head, collaborators)."""
        members = {self.owner}
        if self.project_head:
            members.add(self.project_head)
        for col in self.collaborators.all():
            members.add(col)
        return members


class ProjectTask(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    title = models.CharField(max_length=255)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


# ─── Beta Feature: Custom Report Forms ───────────────────────────────────────
# Slug: 'custom_report_forms'
# This model lives here in the projects app. Beta is just a gate, not a container.
# When this feature graduates to stable, it stays here — nothing needs to move.

# Default form configuration — the baseline all projects start with.
# All standard fields are enabled by default.
DEFAULT_FORM_CONFIG = {
    # Which standard fields are shown on the report form (order matters for display)
    "enabled_fields": [
        "title",
        "description",
        "steps",
        "component",
        "frequency",
        "impact",
        "visibility",
    ],
    # Global default frequency choices (used when no per-component override exists)
    "frequency_choices": [
        {"value": "once", "label": "Once"},
        {"value": "daily", "label": "Daily"},
        {"value": "weekly", "label": "Weekly"},
        {"value": "monthly", "label": "Monthly"},
    ],
    # Per-component frequency overrides: {"<component_uuid_str>": [{"value":..., "label":...}]}
    # If a component is not listed here, the global frequency_choices are used.
    "component_frequencies": {},
}

# Fields that are considered important — removing these shows a warning in the UI.
IMPORTANT_FORM_FIELDS = {"title", "description"}


class ReportFormConfig(models.Model):
    """
    Custom report submission form configuration for a project.
    Beta feature slug: 'custom_report_forms'

    The config JSON schema:
    {
        "enabled_fields": ["title", "description", ...],
        "frequency_choices": [{"value": "once", "label": "Once"}, ...],
        "component_frequencies": {
            "<component_uuid>": [{"value": "daily", "label": "Daily"}, ...]
        }
    }

    When this feature graduates to stable, only BetaFeature.status changes.
    This model stays exactly here.
    """
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name='form_config'
    )
    config = models.JSONField(
        default=dict,
        help_text="JSON configuration for the report submission form."
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"FormConfig for {self.project.title}"

    def get_enabled_fields(self) -> list:
        return self.config.get('enabled_fields', DEFAULT_FORM_CONFIG['enabled_fields'])

    def get_frequency_choices(self, component=None) -> list:
        """
        Returns frequency choices for a given component (or global defaults).
        component: Component instance or None.
        """
        if component:
            component_overrides = self.config.get('component_frequencies', {})
            component_uuid_str = str(component.uuid)
            if component_uuid_str in component_overrides:
                return component_overrides[component_uuid_str]
        return self.config.get('frequency_choices', DEFAULT_FORM_CONFIG['frequency_choices'])

    def get_missing_important_fields(self) -> list:
        """Returns any important fields that have been removed from the config."""
        enabled = set(self.get_enabled_fields())
        return list(IMPORTANT_FORM_FIELDS - enabled)