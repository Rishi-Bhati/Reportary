"""
Validation for the custom report form configuration (beta: custom_report_forms).

The configuration is a JSON blob assembled from a large, dynamic POST body. It
was previously written straight from ``request.POST.getlist()`` with no
validation: arbitrary slugs (which are interpolated into inline JS handlers in
the config template), arbitrary field names, arbitrary widget types, and no caps
of any kind on a single unbounded JSONField.

Everything the owner submits goes through :func:`build_form_config` now.
"""
import re

from projects.models import (
    ALLOWED_CUSTOM_FIELD_TYPES,
    ALLOWED_FORM_FIELDS,
    DEFAULT_FORM_CONFIG,
    IMPORTANT_FORM_FIELDS,
)

# Caps. A form configuration is edited by hand in a browser; these are far above
# any legitimate use and exist so one POST cannot inflate the column without limit.
MAX_REPORT_TYPES = 20
MAX_CUSTOM_FIELDS_PER_TYPE = 30
MAX_NAME_LENGTH = 60
MAX_LABEL_LENGTH = 100
MAX_CHOICES_LENGTH = 500
MAX_FREQUENCY_CHOICES = 20
MAX_SLUG_LENGTH = 50

_SLUG_CLEAN = re.compile(r'[^a-z0-9]+')


def normalise_slug(raw: str) -> str:
    """
    Reduce arbitrary text to ``[a-z0-9_]``.

    Matches the client-side slug derivation in configure_report_form.html, and
    guarantees the result is safe to interpolate into the inline ``onclick``
    handlers that template builds.
    """
    if not raw:
        return ''
    slug = _SLUG_CLEAN.sub('_', str(raw).strip().lower()).strip('_')
    return slug[:MAX_SLUG_LENGTH]


def _parse_custom_fields(post, slug, errors):
    """Build the custom field list for one report type."""
    names = post.getlist(f'cf_name_{slug}')
    labels = post.getlist(f'cf_label_{slug}')
    types = post.getlist(f'cf_type_{slug}')
    choices = post.getlist(f'cf_choices_{slug}')

    if len(names) > MAX_CUSTOM_FIELDS_PER_TYPE:
        errors.append(
            f"'{slug}' has {len(names)} custom fields; the maximum is "
            f"{MAX_CUSTOM_FIELDS_PER_TYPE}. The extra fields were not saved."
        )
        names = names[:MAX_CUSTOM_FIELDS_PER_TYPE]

    fields = []
    seen = set()
    for index, raw_name in enumerate(names):
        name = normalise_slug(raw_name)[:MAX_NAME_LENGTH]
        if not name:
            continue
        if name in seen:
            errors.append(f"'{slug}' has more than one custom field named '{name}'; only the first was kept.")
            continue
        seen.add(name)

        label = (labels[index].strip() if index < len(labels) else '') or name.replace('_', ' ').title()
        label = label[:MAX_LABEL_LENGTH]

        field_type = (types[index].strip() if index < len(types) else '') or 'text'
        if field_type not in ALLOWED_CUSTOM_FIELD_TYPES:
            errors.append(
                f"'{label}' had an unsupported field type '{field_type}'; it was saved as a text field."
            )
            field_type = 'text'

        choice_str = (choices[index].strip() if index < len(choices) else '')[:MAX_CHOICES_LENGTH]
        if field_type == 'select':
            options = [c.strip() for c in choice_str.split(',') if c.strip()]
            if not options:
                errors.append(
                    f"'{label}' is a dropdown with no choices, so nobody could fill it in. "
                    f"It was saved as a text field instead."
                )
                field_type = 'text'
                choice_str = ''
            else:
                choice_str = ', '.join(options)

        fields.append({
            'name': name,
            'label': label,
            'type': field_type,
            'choices': choice_str,
            'required': post.get(f'cf_required_{slug}_{index}') == 'true',
        })

    return fields


def _parse_component_frequencies(post, project, errors):
    """Per-component frequency overrides, keyed by component uuid."""
    overrides = {}
    for component in project.components:
        raw = post.get(f'comp_freq_{component.uuid}', '').strip()
        if not raw:
            continue

        parsed = []
        for pair in raw.split(','):
            pair = pair.strip()
            if not pair:
                continue
            if ':' in pair:
                value, label = pair.split(':', 1)
            else:
                value, label = pair, pair.capitalize()
            value = normalise_slug(value)
            label = label.strip()[:MAX_LABEL_LENGTH]
            if value and label:
                parsed.append({'value': value, 'label': label})

        if len(parsed) > MAX_FREQUENCY_CHOICES:
            errors.append(
                f"'{component.name}' had more than {MAX_FREQUENCY_CHOICES} frequency "
                f"options; the extras were dropped."
            )
            parsed = parsed[:MAX_FREQUENCY_CHOICES]
        if parsed:
            overrides[str(component.uuid)] = parsed

    return overrides


def build_form_config(post, project, current_config=None):
    """
    Build a validated form configuration from a POST body.

    Returns ``(config, errors)``. `errors` is a list of human-readable warnings
    describing what was corrected; the returned config is always safe to save.
    """
    errors = []
    current_config = dict(current_config or DEFAULT_FORM_CONFIG)

    raw_slugs = post.getlist('report_type_slugs')
    if len(raw_slugs) > MAX_REPORT_TYPES:
        errors.append(
            f"{len(raw_slugs)} report types were submitted; the maximum is "
            f"{MAX_REPORT_TYPES}. The extras were not saved."
        )
        raw_slugs = raw_slugs[:MAX_REPORT_TYPES]

    report_types = {}
    for raw_slug in raw_slugs:
        slug = normalise_slug(raw_slug)
        if not slug or slug in report_types:
            continue

        name = (post.get(f'report_type_name_{raw_slug}')
                or post.get(f'report_type_name_{slug}')
                or slug.replace('_', ' ').title())
        name = name.strip()[:MAX_LABEL_LENGTH] or slug

        submitted_fields = (post.getlist(f'enabled_fields_{raw_slug}')
                            or post.getlist(f'enabled_fields_{slug}'))
        enabled_fields = [f for f in submitted_fields if f in ALLOWED_FORM_FIELDS]
        dropped = set(submitted_fields) - set(enabled_fields)
        if dropped:
            errors.append(
                f"'{name}' referenced unknown form fields ({', '.join(sorted(dropped))}); they were ignored."
            )

        # title and description back non-nullable model columns. Hiding them
        # forces every report through a generated placeholder, so they are
        # always kept — IMPORTANT_FORM_FIELDS already records why.
        missing_important = IMPORTANT_FORM_FIELDS - set(enabled_fields)
        if missing_important:
            errors.append(
                f"'{name}' cannot hide {', '.join(sorted(missing_important))} — "
                f"reports need them, so they were kept enabled."
            )
            enabled_fields = list(enabled_fields) + sorted(missing_important)

        report_types[slug] = {
            'name': name,
            'enabled_fields': enabled_fields,
            'custom_fields': _parse_custom_fields(post, raw_slug, errors),
        }

    if not report_types:
        report_types = dict(
            current_config.get('report_types') or DEFAULT_FORM_CONFIG['report_types'])

    default_slug = normalise_slug(post.get('default_report_type', ''))
    if default_slug not in report_types:
        if default_slug:
            errors.append(
                f"'{default_slug}' is not one of this project's report types, so the "
                f"default was reset."
            )
        default_slug = next(iter(report_types))

    config = dict(current_config)
    config['report_types'] = report_types
    config['default_report_type'] = default_slug
    # Legacy mirror, kept for graceful degradation elsewhere in the codebase.
    config['enabled_fields'] = report_types[default_slug]['enabled_fields']
    config['component_frequencies'] = _parse_component_frequencies(post, project, errors)
    config.setdefault('frequency_choices', DEFAULT_FORM_CONFIG['frequency_choices'])

    return config, errors
