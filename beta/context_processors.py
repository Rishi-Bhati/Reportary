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
    Adds `beta_features` dict and `app_version` to every template context.
    """
    if not request.user.is_authenticated:
        return {
            'beta_features': {},
            'app_version': 'v1.0.0 - stable'
        }

    from beta.models import UserBetaEnrollment
    is_enrolled = UserBetaEnrollment.objects.filter(user=request.user).exists()
    version = 'v1.1.0-beta.1' if is_enrolled else 'v1.0.0 - stable'

    return {
        'beta_features': get_user_beta_features(request.user),
        'app_version': version
    }
