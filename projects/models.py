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

    def save(self, *args, **kwargs):
        """
        Keep the legacy `public` flag in step with `visibility`.

        The two are a dual source of truth: `rules.can_access_project` switches
        on `visibility` while several list queries still filter on `public`.
        They were synced in exactly one place — ProjectForm.save() — so a
        project created or updated anywhere else (a shell script, a data
        migration, a future API endpoint) would desync and appear in public
        listings while `rules` still considered it private.

        Syncing here makes that impossible regardless of the write path.
        """
        self.public = (self.visibility == 'public')
        if 'update_fields' in kwargs and kwargs['update_fields'] is not None:
            fields = set(kwargs['update_fields'])
            if 'visibility' in fields:
                fields.add('public')
            kwargs['update_fields'] = fields
        super().save(*args, **kwargs)

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
    # Default set of report types (slug -> configuration)
    "report_types": {
        "bug": {
            "name": "Bug Report",
            "enabled_fields": ["title", "description", "steps", "component", "frequency", "impact", "visibility"],
            "custom_fields": []
        },
        "feature": {
            "name": "Feature Request",
            "enabled_fields": ["title", "description", "visibility"],
            "custom_fields": []
        },
        "vulnerability": {
            "name": "Vulnerability Report",
            "enabled_fields": ["title", "description", "impact"],
            "custom_fields": []
        }
    },
    "default_report_type": "bug",
    # Which standard fields are shown on the report form (legacy, kept for backward compatibility/graceful degradation)
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

    def get_report_types_config(self) -> dict:
        """Returns the dictionary of configured report types."""
        return self.config.get('report_types', DEFAULT_FORM_CONFIG['report_types'])

    def get_fields_for_type(self, type_slug: str) -> dict:
        """
        Returns configuration (name, enabled_fields, custom_fields) for a report type.
        Falls back to default configurations if slug not found.
        """
        types = self.get_report_types_config()
        if type_slug in types:
            return types[type_slug]
        defaults = DEFAULT_FORM_CONFIG['report_types']
        if type_slug in defaults:
            return defaults[type_slug]
        return {
            "name": type_slug.replace('_', ' ').title(),
            "enabled_fields": DEFAULT_FORM_CONFIG["enabled_fields"],
            "custom_fields": []
        }

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

# ─── Report type resolution ───────────────────────────────────────────────────

# Standard form fields a project may choose to show or hide. Anything outside
# this set is rejected when a form configuration is saved.
ALLOWED_FORM_FIELDS = frozenset(DEFAULT_FORM_CONFIG["enabled_fields"])

# Custom field widget types the report form knows how to build.
ALLOWED_CUSTOM_FIELD_TYPES = ("text", "textarea", "checkbox", "select")


def resolve_report_type_slug(project, requested_slug=None) -> str:
    """
    Return a report type slug that is valid for `project`.

    Untrusted input (form POST, portal POST, API JSON) must pass through here.
    Report.report_type is a CharField(max_length=50); writing the raw request
    value into it both bypassed the configured choice list and overflowed the
    column on PostgreSQL.
    """
    configured = DEFAULT_FORM_CONFIG["report_types"]
    default_slug = DEFAULT_FORM_CONFIG["default_report_type"]

    if project is not None:
        config = ReportFormConfig.objects.filter(project=project).first()
        if config:
            configured = config.get_report_types_config() or configured
            default_slug = config.config.get("default_report_type", default_slug)

    if default_slug not in configured:
        default_slug = next(iter(configured), "bug")

    if requested_slug and requested_slug in configured:
        return requested_slug
    return default_slug


# Bounds on a single custom field *value*. The injected form fields carried no
# max_length, so an unbounded string could be stored in custom_fields_data.
MAX_CUSTOM_FIELD_LENGTH = 2000
MAX_CUSTOM_TEXTAREA_LENGTH = 10000
