from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.urls import reverse
from django.utils import timezone
from .models import Notification, Invitation
from .services import (
    get_user_notifications,
    mark_informational_as_read,
    mark_as_read,
    mark_as_unread,
    accept_invitation,
    decline_invitation
)

@login_required
def notification_center(request):
    """Renders the user's notification center."""
    user = request.user
    
    # 1. Fetch user notifications
    all_notifications = get_user_notifications(user)
    
    # 2. Get active tab
    active_tab = request.GET.get('tab', 'all')
    
    # 3. Filter notifications based on tab selection
    if active_tab == 'unread':
        notifications = all_notifications.filter(is_read=False)
    elif active_tab == 'invites':
        notifications = all_notifications.filter(requires_action=True)
    else:
        notifications = all_notifications

    # 4. Auto-mark informational/non-actionable notifications as read on opening this page
    mark_informational_as_read(user)

    context = {
        'notifications': notifications,
        'active_tab': active_tab,
        'unread_count': all_notifications.filter(is_read=False).count(),
        'invites_count': all_notifications.filter(requires_action=True, is_read=False).count(),
        'all_count': all_notifications.count(),
    }
    return render(request, "notifications/notification_center.html", context)


@login_required
@require_POST
def toggle_read(request, uuid):
    """Toggles the read/unread status of a notification."""
    notification = get_object_or_404(Notification, uuid=uuid, recipient=request.user)
    
    if notification.is_read:
        mark_as_unread(notification)
        messages.success(request, "Notification marked as unread.")
    else:
        mark_as_read(notification)
        messages.success(request, "Notification marked as read.")
        
    return redirect('notifications:center')


@login_required
@require_POST
def mark_all_read(request):
    """Marks all notifications for the user as read."""
    Notification.objects.filter(recipient=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    messages.success(request, "All notifications marked as read.")
    return redirect('notifications:center')


@login_required
@require_POST
def accept_invite(request, uuid):
    """Handles accepting an invitation."""
    if not request.user.is_email_verified:
        from accounts.views import render_verification_required
        return render_verification_required(request, "Verify your email to accept invitations.")

    invitation = get_object_or_404(Invitation, uuid=uuid, invited_user=request.user)
    
    try:
        accept_invitation(invitation, request.user)
        messages.success(request, f"Invitation accepted successfully!")
        
        # Redirect user to the target project or organisation
        if invitation.invite_type in ['collaborator', 'project_head'] and invitation.project:
            return redirect('projects:project_detail', project_uuid=invitation.project.uuid)
        elif invitation.invite_type == 'organisation' and invitation.organisation:
            return redirect('organisations:dashboard', uuid=invitation.organisation.uuid)
    except PermissionError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, "An error occurred while accepting the invitation.")
        
    return redirect('notifications:center')


@login_required
@require_POST
def decline_invite(request, uuid):
    """Handles declining an invitation."""
    if not request.user.is_email_verified:
        from accounts.views import render_verification_required
        return render_verification_required(request, "Verify your email to decline invitations.")

    invitation = get_object_or_404(Invitation, uuid=uuid, invited_user=request.user)
    
    try:
        decline_invitation(invitation, request.user)
        messages.info(request, "Invitation declined.")
    except PermissionError as e:
        messages.error(request, str(e))
    except Exception as e:
        messages.error(request, "An error occurred while declining the invitation.")
        
    return redirect('notifications:center')
