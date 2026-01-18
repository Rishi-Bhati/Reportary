from .models import AuditLog

def get_entity_history(entity_type, entity_id):
    return AuditLog.objects.filter(
        entity_type=entity_type,
        entity_id=str(entity_id)
    ).order_by("-created_at")


def log_action(
    *,
    actor,
    action,
    entity_type,
    entity_id,
    field_name=None,
    old_value=None,
    new_value=None,
):
    AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
    )

