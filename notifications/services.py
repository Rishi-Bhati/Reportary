from django.utils import timezone
from audit.services import log_action
from .models import Notification, Invitation
from .constants import AUTO_READ_TYPES
from .email_service import send_notification_email

def create_notification(*, recipient, actor, notification_type, title, message, target_content_type, target_uuid, requires_action=False):
    """Creates an in-app notification and sends an email notification."""
    # Prevent duplicate informational notifications for the same event
    # e.g., if a user gets notified about the same comment multiple times
    notification = Notification.objects.create(
        recipient=recipient,
        actor=actor,
        notification_type=notification_type,
        title=title,
        message=message,
        target_content_type=target_content_type,
        target_uuid=target_uuid,
        requires_action=requires_action
    )

    # Determine email recipient list
    # For report updates: TO is assigned_to/project owner, CC is collaborators + reporter
    # For comments: same
    # But send_notification_email will format the context and send it.
    
    # We trigger the email sending asynchronously or synchronously depending on settings.
    # We will pass context down to the email service.
    context = {
        'title': title,
        'message': message,
        'actor_username': actor.username,
        'recipient_username': recipient.username,
        'target_uuid': str(target_uuid),
        'target_type': target_content_type,
    }
    
    # Determine recipients and send
    to_emails = [recipient.email]
    cc_emails = []
    
    # Let's get related object to populate CC
    if target_content_type == 'report':
        try:
            from reports.models import Report
            report = Report.objects.get(uuid=target_uuid)
            context['report_title'] = report.title
            context['project_title'] = report.project.title
            
            # Add CCs: Collaborators + Reporter (excluding recipient and actor)
            cc_users = set()
            if report.reported_by:
                cc_users.add(report.reported_by)
            for c in report.project.collaborators.all():
                cc_users.add(c)
            if report.project.owner:
                cc_users.add(report.project.owner)
            if report.project.project_head:
                cc_users.add(report.project.project_head)
                
            cc_emails = [
                u.email for u in cc_users 
                if u.email and u.email != recipient.email and u != actor
            ]
        except Exception:
            pass
    elif target_content_type == 'project':
        try:
            from projects.models import Project
            project = Project.objects.get(uuid=target_uuid)
            context['project_title'] = project.title
        except Exception:
            pass
    elif target_content_type == 'organisation':
        try:
            from organisations.models import Organisation
            org = Organisation.objects.get(uuid=target_uuid)
            context['organisation_name'] = org.name
        except Exception:
            pass

    try:
        send_notification_email(
            notification_type=notification_type,
            subject=title,
            context=context,
            to_emails=to_emails,
            cc_emails=cc_emails
        )
    except Exception as e:
        # Log email sending failure but don't crash user request
        print(f"Failed to send email notification: {e}")

    return notification


def create_invitation(*, invite_type, invited_by, invited_user, project=None, organisation=None):
    """Creates a pending invitation and associated action notification."""
    if not invited_user.is_email_verified:
        raise PermissionError(f"The user '{invited_user.email}' has not verified their email yet and cannot be invited.")

    # Check if a pending invite already exists to prevent duplicate spamming
    existing = Invitation.objects.filter(
        invite_type=invite_type,
        invited_user=invited_user,
        project=project,
        organisation=organisation,
        status='pending'
    ).first()
    if existing:
        return existing

    # Define notification message
    if invite_type == 'collaborator':
        title = "Project Collaboration Invitation"
        message = f"{invited_by.username} has invited you to collaborate on the project '{project.title}'."
        target_type = 'project'
        target_uuid = project.uuid
    elif invite_type == 'organisation':
        title = "Organisation Membership Invitation"
        message = f"{invited_by.username} has invited you to join the organisation '{organisation.name}'."
        target_type = 'organisation'
        target_uuid = organisation.uuid
    elif invite_type == 'project_head':
        title = "Project Head Designation Invitation"
        message = f"{invited_by.username} has designated you as the Project Head for '{project.title}'."
        target_type = 'project'
        target_uuid = project.uuid
    else:
        raise ValueError(f"Unknown invite type: {invite_type}")

    # Step 1: Create actionable notification
    notification = create_notification(
        recipient=invited_user,
        actor=invited_by,
        notification_type=f"invite_{invite_type}",
        title=title,
        message=message,
        target_content_type=target_type,
        target_uuid=target_uuid,
        requires_action=True
    )

    # Step 2: Create Invitation record
    invitation = Invitation.objects.create(
        invite_type=invite_type,
        invited_by=invited_by,
        invited_user=invited_user,
        project=project,
        organisation=organisation,
        notification=notification,
        status='pending'
    )

    return invitation


def accept_invitation(invitation, user):
    """Accepts an invitation and applies changes."""
    if invitation.invited_user != user:
        raise PermissionError("You can only accept invitations sent to you.")
    
    if invitation.status != 'pending':
        return invitation  # Already processed

    invitation.status = 'accepted'
    invitation.responded_at = timezone.now()
    invitation.save()

    # Mark associated notification as read
    mark_as_read(invitation.notification)

    # Apply changes based on invite type
    if invitation.invite_type == 'collaborator':
        project = invitation.project
        project.collaborators.add(user)
        log_action(
            actor=user,
            action="update",
            entity_type="Project",
            entity_id=project.uuid,
            field_name="collaborators",
            old_value="Accept Invitation",
            new_value=f"Added collaborator: {user.email}",
        )
        
        # Notify the inviter that user accepted
        create_notification(
            recipient=invitation.invited_by,
            actor=user,
            notification_type='collaborator_added',
            title="Collaboration Invitation Accepted",
            message=f"{user.username} has accepted your invitation to collaborate on project '{project.title}'.",
            target_content_type='project',
            target_uuid=project.uuid
        )

    elif invitation.invite_type == 'organisation':
        org = invitation.organisation
        org.members.add(user)
        log_action(
            actor=user,
            action="update",
            entity_type="Organisation",
            entity_id=org.uuid,
            field_name="members",
            old_value="Accept Invitation",
            new_value=f"Added member: {user.email}",
        )
        
        # Notify the inviter that user accepted
        create_notification(
            recipient=invitation.invited_by,
            actor=user,
            notification_type='collaborator_added',
            title="Organisation Invitation Accepted",
            message=f"{user.username} has accepted your invitation to join organisation '{org.name}'.",
            target_content_type='organisation',
            target_uuid=org.uuid
        )

    elif invitation.invite_type == 'project_head':
        project = invitation.project
        # Keep track of old project head
        old_head = project.project_head
        project.project_head = user
        project.save()
        log_action(
            actor=user,
            action="update",
            entity_type="Project",
            entity_id=project.uuid,
            field_name="project_head",
            old_value=old_head.email if old_head else None,
            new_value=user.email,
        )
        
        # Notify the inviter that user accepted
        create_notification(
            recipient=invitation.invited_by,
            actor=user,
            notification_type='collaborator_added',
            title="Project Head Designation Accepted",
            message=f"{user.username} has accepted your designation as Project Head for '{project.title}'.",
            target_content_type='project',
            target_uuid=project.uuid
        )

    return invitation


def decline_invitation(invitation, user):
    """Declines an invitation."""
    if invitation.invited_user != user:
        raise PermissionError("You can only decline invitations sent to you.")
    
    if invitation.status != 'pending':
        return invitation  # Already processed

    invitation.status = 'declined'
    invitation.responded_at = timezone.now()
    invitation.save()

    # Mark associated notification as read
    mark_as_read(invitation.notification)

    # Notify the inviter that user declined
    target_title = invitation.project.title if invitation.project else invitation.organisation.name
    target_type = 'project' if invitation.project else 'organisation'
    target_uuid = invitation.project.uuid if invitation.project else invitation.organisation.uuid
    
    create_notification(
        recipient=invitation.invited_by,
        actor=user,
        notification_type='collaborator_added',
        title=f"Invitation Declined",
        message=f"{user.username} has declined your invitation for '{target_title}'.",
        target_content_type=target_type,
        target_uuid=target_uuid
    )

    return invitation


def mark_as_read(notification):
    """Marks a single notification as read."""
    if not notification.is_read:
        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()
    return notification


def mark_as_unread(notification):
    """Marks a single notification as unread."""
    if notification.is_read:
        notification.is_read = False
        notification.read_at = None
        notification.save()
    return notification


def mark_informational_as_read(user):
    """Bulk marks all non-actionable notifications for a user as read."""
    Notification.objects.filter(
        recipient=user,
        is_read=False,
        notification_type__in=AUTO_READ_TYPES
    ).update(
        is_read=True,
        read_at=timezone.now()
    )


def get_unread_count(user):
    """Returns the count of unread notifications for a user."""
    if not user.is_authenticated:
        return 0
    return Notification.objects.filter(recipient=user, is_read=False).count()


def get_user_notifications(user):
    """Returns all notifications for a user."""
    return Notification.objects.filter(recipient=user).order_by('-created_at')
