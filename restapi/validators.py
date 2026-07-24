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
