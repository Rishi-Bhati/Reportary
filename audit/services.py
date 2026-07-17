from .models import AuditLog

# M-12: Fields whose values must never appear in audit logs in plaintext
_SENSITIVE_FIELDS = frozenset({
    'password', 'secret_key', 'secret', 'token', 'api_key', 'api_secret',
    'access_token', 'refresh_token', 'private_key', 'auth_token',
})

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
    parent_type=None,
    parent_id=None,
    field_name=None,
    old_value=None,
    new_value=None,
):
    # M-12: Redact sensitive field values before persisting
    if field_name and field_name.lower() in _SENSITIVE_FIELDS:
        old_value = '[REDACTED]'
        new_value = '[REDACTED]'

    AuditLog.objects.create(
        actor=actor,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        parent_type=parent_type,
        parent_id=str(parent_id) if parent_id is not None else None,
        field_name=field_name,
        old_value=str(old_value) if old_value is not None else None,
        new_value=str(new_value) if new_value is not None else None,
    )

