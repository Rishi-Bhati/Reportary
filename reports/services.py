from audit.services import log_action, get_entity_history
import rules.views as rules
from accounts.models import User
from .models import Report

def assign_report(*, request, report, assignee, actor):
    old = report.assigned_to

    if request.method == 'POST':
        assignee_id = request.POST.get('assignee')
        if assignee_id:
            try:
                assignee = User.objects.get(uuid=assignee_id)
                report.assigned_to = assignee
                report.save()
            except User.DoesNotExist:
                pass

    log_action(
        actor=actor,
        action="update",
        entity_type="Report",
        entity_id=report.uuid,
        field_name="assigned_to",
        old_value=old.email if old else None,
        new_value=assignee.email,
    )

    if report.assigned_to != old:
        from notifications.services import create_notification
        if report.assigned_to and report.assigned_to != actor:
            create_notification(
                recipient=report.assigned_to,
                actor=actor,
                notification_type='report_assigned',
                title="Report Assigned",
                message=f"Report '{report.title}' has been assigned to you by {actor.username}.",
                target_content_type='report',
                target_uuid=report.uuid
            )

    return report



def update_report_status(*, request, report, new_status, actor):
    old_status = report.status

    if old_status == new_status:
        return report  # no-op

    if new_status and new_status in [choice[0] for choice in Report.STATUS_CHOICES]:
        report.status = new_status
        report.save()

    log_action(
        actor=actor,
        action="update",
        entity_type="Report",
        entity_id=report.uuid,
        field_name="status",
        old_value=old_status,
        new_value=new_status,
    )

    from notifications.services import create_notification
    followers = [f.user for f in report.followers.select_related('user')]
    recipients = {report.assigned_to, report.reported_by, report.project.owner, report.project.project_head} | set(followers)
    for recipient in recipients:
        if recipient and recipient != actor:
            create_notification(
                recipient=recipient,
                actor=actor,
                notification_type='report_status_changed',
                title="Report Status Changed",
                message=f"Report '{report.title}' status was changed from '{old_status}' to '{new_status}' by {actor.username}.",
                target_content_type='report',
                target_uuid=report.uuid,
                extra_context={
                    'old_status': old_status,
                    'new_status': new_status,
                }
            )

    return report

def update_report_impact(*, report, new_impact, actor):

    old_impact = report.impact

    if old_impact == new_impact:
        return report  # no-op

    if new_impact and new_impact in [choice[0] for choice in Report.IMPACT_CHOICES]:
        report.impact = new_impact
        report.save()
    
    log_action(
        actor=actor,
        action="update",
        entity_type="Report",
        entity_id=report.uuid,
        field_name="impact",
        old_value=old_impact,
        new_value=new_impact,
    )

    from notifications.services import create_notification
    followers = [f.user for f in report.followers.select_related('user')]
    recipients = {report.assigned_to, report.reported_by, report.project.owner, report.project.project_head} | set(followers)
    for recipient in recipients:
        if recipient and recipient != actor:
            create_notification(
                recipient=recipient,
                actor=actor,
                notification_type='report_impact_changed',
                title="Report Impact Changed",
                message=f"Report '{report.title}' impact was changed from '{old_impact}' to '{new_impact}' by {actor.username}.",
                target_content_type='report',
                target_uuid=report.uuid
            )

    return report


def update_report_visibility(*, report, new_visibility, actor):

    old_visibility = report.visibility

    if old_visibility == new_visibility:
        return report  # no-op

    report.visibility = new_visibility
    report.save()
    
    log_action(
        actor=actor,
        action="update",
        entity_type="Report",
        entity_id=report.uuid,
        field_name="visibility",
        old_value=old_visibility,
        new_value=new_visibility,
    )
    return report

def get_report_history(user, report):
    if rules.can_see_history(user, report):
        return get_entity_history("Report", report.uuid)
    return []


def toggle_report_bookmark(*, user, report):
    from .models import ReportBookmark
    bookmark, created = ReportBookmark.objects.get_or_create(user=user, report=report)
    if not created:
        bookmark.delete()
        return False
    return True


def toggle_report_follower(*, user, report):
    from .models import ReportFollower
    follower, created = ReportFollower.objects.get_or_create(user=user, report=report)
    if not created:
        follower.delete()
        return False
    return True


def users_in_reports(reports_qs):
    """
    Users appearing as reporter or assignee on the given reports.

    The report-list filter dropdowns previously used ``User.objects.all()``,
    which rendered the entire user table into every list — including the
    unauthenticated public-project view, making every registered username
    enumerable by anyone. Scoping to participants fixes that and removes the
    page's worst weight problem at the same time.
    """
    from django.db.models import Q
    from accounts.models import User

    ids = reports_qs.order_by().values('reported_by')
    assignee_ids = reports_qs.order_by().values('assigned_to')
    return User.objects.filter(
        Q(pk__in=ids) | Q(pk__in=assignee_ids)
    ).distinct().order_by('username')


# ─── Attachment validation ────────────────────────────────────────────────────

MAX_ATTACHMENT_BYTES = 10 * 1024 * 1024  # 10 MB


def attachment_extension(filename: str) -> str:
    """Lowercased extension including the dot, or '' if there isn't one."""
    if not filename or '.' not in filename:
        return ''
    return '.' + filename.rsplit('.', 1)[-1].lower()


def allowed_attachment_extensions(project) -> list:
    return [ext.strip().lower()
            for ext in (project.allowed_attachment_types or '').split(',')
            if ext.strip()]


def validate_attachment(uploaded_file, project):
    """
    Validate one upload against the project's rules.

    Shared by the authenticated and anonymous submission paths. They had
    different rules: the authenticated path checked the extension allowlist but
    had no size limit at all, while the anonymous path — the one that accepts
    files from strangers — checked size but ignored the allowlist entirely.

    Raises django.forms.ValidationError.
    """
    from django import forms

    if uploaded_file is None:
        return uploaded_file

    if uploaded_file.size > MAX_ATTACHMENT_BYTES:
        raise forms.ValidationError(
            f"'{uploaded_file.name}' is too large. Maximum size is "
            f"{MAX_ATTACHMENT_BYTES // (1024 * 1024)} MB."
        )

    allowed = allowed_attachment_extensions(project) if project else []
    if allowed:
        extension = attachment_extension(uploaded_file.name)
        if extension not in allowed:
            raise forms.ValidationError(
                f"File type '{extension or 'unknown'}' is not allowed for "
                f"'{uploaded_file.name}'. Allowed types: {', '.join(allowed)}."
            )

    return uploaded_file


def components_in_reports(reports_qs):
    """
    Components referenced by the given reports.

    Same reasoning as users_in_reports: the personal list views built this
    dropdown from Component.objects.all(), exposing the component names of every
    project in the system — including private ones.
    """
    from components.models import Component

    return Component.objects.filter(
        pk__in=reports_qs.order_by().values('component')
    ).distinct().order_by('name')
