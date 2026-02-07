from audit.services import log_action, get_entity_history
import rules.views as rules
from accounts.models import User
from .models import Project
from audit.models import AuditLog
from components.models import Component
from django.utils import timezone
from datetime import timedelta


def track_component_deletions(*, formset, actor, project):
    # --- Handle component deletions ---
    for form in formset.deleted_forms:
        if form.instance and form.instance.pk:
            log_action(
                actor=actor,
                action="delete",
                entity_type="Component",
                entity_id=form.instance.pk,
                parent_type="Project",
                parent_id=project.id,
                field_name="name",
                old_value=form.instance.name,
            )

def track_component_additions_and_modifications(*, formset, actor, project):
    # --- Handle component additions ---
    for component in formset.new_objects:
        log_action(
            actor=actor,
            action="create",
            entity_type="Component",
            entity_id=component.uuid,
            parent_type="Project",
            parent_id=project.uuid,
            field_name="name",
            new_value=component.name,
        )

    # --- Handle component modifications ---
    for form in formset.forms:
        # Skip new forms (already logged) and deleted forms
        if form.instance in formset.new_objects or form.cleaned_data.get('DELETE'):
            continue

        if form.has_changed():
            for field in form.changed_data:
                log_action(
                    actor=actor,
                    action="update",
                    entity_type="Component",
                    entity_id=form.instance.pk,
                    parent_type="Project",
                    parent_id=project.uuid,
                    field_name=field,
                    old_value=form.initial.get(field),
                    new_value=form.cleaned_data.get(field),
                )


def update_project(
    *,
    project,
    form,
    component_formset,
    collaborator_emails,
    actor
):
    # ---- Track field changes (Project model) ----
    changed_fields = {}

    for field in form.changed_data:
        old = getattr(project, field)
        new = form.cleaned_data[field]
        changed_fields[field] = (old, new)

    project = form.save()

    # ---- Save components (treat as bulk update) ----
    if component_formset.has_changed():
        track_component_deletions(formset=component_formset, actor=actor, project=project)
        component_formset.save()
        track_component_additions_and_modifications(formset=component_formset, actor=actor, project=project)
        log_action(
            actor=actor,
            action="update",
            entity_type="Project",
            entity_id=project.uuid,
            field_name="components",
            old_value="---",
            new_value="Components were updated",
        )

    # ---- Collaborators diffing ----
    old_collaborators = set(project.collaborators.values_list("id", flat=True))

    project.collaborators.clear()
    project.collaborators.add(actor)

    new_collaborators = {actor.id}

    if collaborator_emails:
        emails = [e.strip() for e in collaborator_emails.split(",")]
        for email in emails:
            user = User.objects.filter(email=email).first()
            if user:
                project.collaborators.add(user)
                new_collaborators.add(user.uuid)

    # ---- Audit logs ----

    # Field-level logs
    for field, (old, new) in changed_fields.items():
        log_action(
            actor=actor,
            action="update",
            entity_type="Project",
            entity_id=project.uuid,
            field_name=field,
            old_value=old,
            new_value=new,
        )

    # Collaborator changes (log as grouped change)
    if old_collaborators != new_collaborators:
        log_action(
            actor=actor,
            action="update",
            entity_type="Project",
            entity_id=project.uuid,
            field_name="collaborators",
            old_value=list(old_collaborators),
            new_value=list(new_collaborators),
        )

    return project

def get_project_history(user, project):
    if rules.is_project_member(user, project):
        return get_entity_history("Project", project.uuid)
    return []


def get_component_changes_for_project_log(project_id, log_entry):
    """
    Get all component changes (create, update, delete) for a specific project log entry.
    This queries for all Component logs with the same project_id as parent, created within 5 seconds of the project log.
    """
    # Use a 5-second window to account for slight timing differences
    time_window_start = log_entry.created_at - timedelta(seconds=5)
    time_window_end = log_entry.created_at + timedelta(seconds=5)
    
    component_logs = AuditLog.objects.filter(
        entity_type="Component",
        parent_type="Project",
        parent_id=str(project_id),
        created_at__gte=time_window_start,
        created_at__lte=time_window_end,
        actor=log_entry.actor
    ).order_by("action", "entity_id")
    
    # Group by entity_id and action
    changes = {}
    for log in component_logs:
        key = log.entity_id
        if key not in changes:
            # Try to get component name, fallback to ID if not found
            try:
                component = Component.objects.get(id=log.entity_id)
                component_name = component.name
            except Component.DoesNotExist:
                component_name = f"Component (ID: {log.entity_id})"
            
            changes[key] = {
                'id': log.entity_id,
                'name': component_name,
                'actions': [],
                'logs': []
            }
        changes[key]['actions'].append(log.action)
        changes[key]['logs'].append(log)
    
    return list(changes.values())