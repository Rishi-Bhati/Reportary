"""
beta/context_processors.py

Injects beta feature flags into every template context.

Usage in templates:
    {% if beta_features.custom_report_forms %}
        <a href="...">Configure Custom Form</a>
    {% endif %}

    {% if beta_features.portal_custom_styling %}
        ...
    {% endif %}
"""
from beta.utils import get_user_beta_features


def beta_features(request):
    """
    Adds `beta_features` dict to every template context.
    Returns empty dict for anonymous users (no DB hit).
    """
    if not request.user.is_authenticated:
        return {'beta_features': {}}

    return {
        'beta_features': get_user_beta_features(request.user)
    }
