from django.db import models
from django.conf import settings
from uuid6 import uuid7

class Notification(models.Model):
    """In-app notification for a user."""
    
    NOTIFICATION_TYPES = [
        # Informational (auto-read on page open)
        ('report_assigned', 'Report Assigned'),
        ('report_reassigned', 'Report Reassigned'),
        ('report_status_changed', 'Report Status Changed'),
        ('report_commented', 'New Comment'),
        ('collaborator_added', 'Added as Collaborator'),
        ('report_impact_changed', 'Report Impact Changed'),
        # Actionable (requires accept/decline, NOT auto-read)
        ('invite_collaborator', 'Collaboration Invite'),
        ('invite_organisation', 'Organisation Invite'),
        ('invite_project_head', 'Project Head Invite'),
    ]
    
    uuid = models.UUIDField(
        default=uuid7,
        editable=False,
        unique=True,
        db_index=True,
    )
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='triggered_notifications'
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # Link to related object (polymorphic style using target_content_type + target_uuid)
    target_content_type = models.CharField(max_length=100)  # 'report', 'project', 'organisation'
    target_uuid = models.UUIDField()
    
    is_read = models.BooleanField(default=False)
    requires_action = models.BooleanField(default=False)  # True for invites
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.notification_type} for {self.recipient.username} (Read: {self.is_read})"


class Invitation(models.Model):
    """Tracks pending invitations that require accept/decline."""
    
    INVITE_TYPES = [
        ('collaborator', 'Project Collaborator'),
        ('organisation', 'Organisation Member'),
        ('project_head', 'Project Head'),
    ]
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
    ]
    
    uuid = models.UUIDField(
        default=uuid7,
        editable=False,
        unique=True,
        db_index=True,
    )
    invite_type = models.CharField(max_length=50, choices=INVITE_TYPES)
    invited_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='sent_invitations'
    )
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='received_invitations'
    )
    
    # Target references (optional depending on type)
    project = models.ForeignKey(
        'projects.Project',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invitations'
    )
    organisation = models.ForeignKey(
        'organisations.Organisation',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='invitations'
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notification = models.OneToOneField(
        Notification,
        on_delete=models.CASCADE,
        related_name='invitation'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.invite_type} invite for {self.invited_user.username} ({self.status})"
