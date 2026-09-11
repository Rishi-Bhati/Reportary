"""
restapi/validators.py

Strict server-side validation for all API payloads.
ALL incoming data is treated as untrusted regardless of authentication status.

Never use form data or request data directly — always pass through a validator.
"""
from django.http import JsonResponse


VALID_FREQUENCY = {'once', 'daily', 'weekly', 'monthly'}
VALID_IMPACT = {'low', 'medium', 'high', 'critical'}
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 10000
MAX_STEPS_LENGTH = 5000
MAX_NAME_LENGTH = 100


class ValidationError(Exception):
    def __init__(self, errors: dict):
        self.errors = errors
        super().__init__(str(errors))


def _require_str(data: dict, field: str, max_length: int, required: bool = True) -> str | None:
    """Validate a string field."""
    value = data.get(field)
    if value is None or value == '':
        if required:
            raise ValidationError({field: f"'{field}' is required."})
        return None
    if not isinstance(value, str):
        raise ValidationError({field: f"'{field}' must be a string."})
    value = value.strip()
    if not value and required:
        raise ValidationError({field: f"'{field}' must not be blank."})
    if len(value) > max_length:
        raise ValidationError({field: f"'{field}' must be at most {max_length} characters."})
    return value


def _require_enum(data: dict, field: str, choices: set, required: bool = False):
    """Validate an enum/choice field."""
    value = data.get(field)
    if value is None:
        if required:
            raise ValidationError({field: f"'{field}' is required."})
        return None
    if not isinstance(value, str) or value not in choices:
        raise ValidationError({field: f"'{field}' must be one of: {sorted(choices)}"})
    return value


def validate_create_report(data: dict) -> dict:
    """
    Validate payload for POST /api/v1/reports/
    Returns cleaned data dict on success.
    Raises ValidationError on failure.
    """
    errors = {}
    cleaned = {}

    try:
        cleaned['title'] = _require_str(data, 'title', MAX_TITLE_LENGTH, required=True)
    except ValidationError as e:
        errors.update(e.errors)

    try:
        cleaned['description'] = _require_str(data, 'description', MAX_DESCRIPTION_LENGTH, required=True)
    except ValidationError as e:
        errors.update(e.errors)

    try:
        steps = _require_str(data, 'steps', MAX_STEPS_LENGTH, required=False)
        cleaned['steps'] = steps or ''
    except ValidationError as e:
        errors.update(e.errors)

    try:
        freq = _require_enum(data, 'frequency', VALID_FREQUENCY, required=False)
        cleaned['frequency'] = freq or 'once'
    except ValidationError as e:
        errors.update(e.errors)

    try:
        impact = _require_enum(data, 'impact', VALID_IMPACT, required=False)
        cleaned['impact'] = impact or 'low'
    except ValidationError as e:
        errors.update(e.errors)

    # component_uuid — optional, validated against project's components in the view
    component_uuid = data.get('component_uuid')
    if component_uuid is not None:
        if not isinstance(component_uuid, str) or len(component_uuid) > 40:
            errors['component_uuid'] = "'component_uuid' must be a valid UUID string."
        else:
            cleaned['component_uuid'] = component_uuid.strip()

    try:
        cleaned['report_type'] = _require_str(data, 'report_type', 50, required=False) or 'bug'
    except ValidationError as e:
        errors.update(e.errors)

    custom_fields = data.get('custom_fields')
    if custom_fields is not None:
        if not isinstance(custom_fields, dict):
            errors['custom_fields'] = "'custom_fields' must be a JSON object (key-value pairs)."
        else:
            cleaned['custom_fields'] = custom_fields
    else:
        cleaned['custom_fields'] = {}

    if errors:
        raise ValidationError(errors)

    return cleaned


def validation_error_response(exc: ValidationError) -> JsonResponse:
    """Convert a ValidationError into a 400 JSON response."""
    return JsonResponse({'error': 'Validation failed.', 'details': exc.errors}, status=400)


# ─── Custom fields ────────────────────────────────────────────────────────────

MAX_CUSTOM_FIELD_VALUE_LENGTH = 2000
MAX_CUSTOM_TEXTAREA_VALUE_LENGTH = 10000


def validate_custom_fields(payload: dict, schema: list, report_type_slug: str) -> dict:
    """
    Validate a custom_fields payload against a project's schema.

    Returns a dict containing only schema-defined keys, with values coerced to
    the declared type. Unknown keys are dropped rather than stored: the payload
    used to pass through on nothing more than an isinstance(dict) check, so any
    JSON of any size was persisted and later rendered on the report page.
    """
    errors = {}
    cleaned = {}

    for field in schema:
        name = field.get('name')
        if not name:
            continue

        field_type = field.get('type') or 'text'
        required = bool(field.get('required', False))
        present = name in payload
        value = payload.get(name)

        if not present or value is None or value == '':
            if required:
                errors[name] = (
                    f"'{name}' is required for report type '{report_type_slug}'."
                )
            continue

        if field_type == 'checkbox':
            if not isinstance(value, bool):
                errors[name] = f"'{name}' must be true or false."
                continue
            cleaned[name] = value

        elif field_type == 'select':
            options = [c.strip() for c in (field.get('choices') or '').split(',') if c.strip()]
            if not isinstance(value, str) or value not in options:
                errors[name] = f"'{name}' must be one of: {options}"
                continue
            cleaned[name] = value

        else:  # text / textarea / anything unrecognised
            if not isinstance(value, str):
                errors[name] = f"'{name}' must be a string."
                continue
            limit = (MAX_CUSTOM_TEXTAREA_VALUE_LENGTH if field_type == 'textarea'
                     else MAX_CUSTOM_FIELD_VALUE_LENGTH)
            if len(value) > limit:
                errors[name] = f"'{name}' must be at most {limit} characters."
                continue
            cleaned[name] = value

    unknown = set(payload) - {f.get('name') for f in schema}
    if unknown:
        errors['custom_fields'] = (
            f"Unknown custom field(s) for report type '{report_type_slug}': "
            f"{sorted(unknown)}"
        )

    if errors:
        raise ValidationError(errors)
    return cleaned
