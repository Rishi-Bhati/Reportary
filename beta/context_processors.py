"""
beta/context_processors.py

Injects beta feature flags into every template context.

Usage in templates:
    {% if beta_features.custom_report_forms %}
        <a href="...">Configure Custom Form</a>
    {% endif %}

This runs on every render, so it must stay cheap — see beta.utils for the
query-count constraints it works under.
"""
from beta.utils import get_feature_registry, get_user_beta_features
from core.version import BETA_VERSION, STABLE_VERSION


def beta_features(request):
    """Adds `beta_features` dict and `app_version` to every template context."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return {'beta_features': {}, 'app_version': STABLE_VERSION}

    from beta.models import UserBetaEnrollment

    features = get_user_beta_features(user)
    # "Enrolled" means the user personally opted in — a project-level grant does
    # not change which build of the app they consider themselves to be on.
    is_enrolled = UserBetaEnrollment.objects.filter(user=user).exists()

    return {
        'beta_features': features,
        'app_version': BETA_VERSION if is_enrolled else STABLE_VERSION,
    }
