from audit.services import log_action
from accounts.models import User
from .models import Report

def assign_report(*, request, report, assignee, actor):
    old = report.assigned_to

    if request.method == 'POST':
        assignee_id = request.POST.get('assignee')
        if assignee_id:
            try:
                assignee = User.objects.get(pk=assignee_id)
                report.assigned_to = assignee
                report.save()
            except User.DoesNotExist:
                pass

    log_action(
        actor=actor,
        action="update",
        entity_type="Report",
        entity_id=report.id,
        field_name="assigned_to",
        old_value=old.email if old else None,
        new_value=assignee.email,
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
        entity_id=report.id,
        field_name="status",
        old_value=old_status,
        new_value=new_status,
    )

    return report
