"""
beta/utils.py

The single gate for all beta feature access checks.
Use these functions everywhere — views, forms, templates (via context_processors).

Usage:
    from beta.utils import user_has_feature

    if user_has_feature(request.user, 'custom_report_forms', project=project):
        # show beta feature

Performance note: `get_user_beta_features` runs on every template render via the
context processor. It resolves the whole feature dict from one cached registry
plus at most two enrollment queries. It previously re-queried BetaFeature and
UserBetaEnrollment once per feature, costing 8–11 queries on every page in the
application and growing with each new feature added.
"""
import logging

logger = logging.getLogger(__name__)

# Feature registry cache. The registry changes only through the Django admin,
# and `invalidate_feature_registry` is wired to BetaFeature save/delete.
FEATURE_REGISTRY_CACHE_KEY = 'beta:feature_registry:v1'
FEATURE_REGISTRY_CACHE_TTL = 300  # seconds


def get_feature_registry() -> dict:
    """
    Returns {slug: {'status': str, 'is_enrollable': bool}} for every feature.
    """
    from django.core.cache import cache

    registry = cache.get(FEATURE_REGISTRY_CACHE_KEY)
    if registry is None:
        from beta.models import BetaFeature

        registry = {
            f.slug: {'status': f.status, 'is_enrollable': f.is_enrollable}
            for f in BetaFeature.objects.only('slug', 'status', 'is_enrollable')
        }
        cache.set(FEATURE_REGISTRY_CACHE_KEY, registry, FEATURE_REGISTRY_CACHE_TTL)
    return registry


def invalidate_feature_registry(**kwargs):
    """Drop the cached registry. Connected to BetaFeature post_save/post_delete."""
    from django.core.cache import cache

    cache.delete(FEATURE_REGISTRY_CACHE_KEY)


def _blanket_slugs(registry: dict) -> frozenset:
    """
    Slugs granted by an enrollment with an empty feature set.

    `is_enrollable=False` marks experimental or internal features that are hidden
    from the enrollment UI. They must be excluded here — including them meant a
    hidden feature was silently switched on for every blanket-enrolled user,
    which is the opposite of what the flag is for.
    """
    return frozenset(
        slug for slug, meta in registry.items()
        if meta['is_enrollable'] and meta['status'] == 'beta'
    )


def _slugs_for_enrollment(enrollment, registry: dict) -> frozenset:
    """Slugs an enrollment row grants. Empty feature set means 'all enrollable'."""
    if enrollment is None:
        return frozenset()
    chosen = frozenset(enrollment.features.values_list('slug', flat=True))
    return chosen or _blanket_slugs(registry)


def _project_granted_slugs(project, registry: dict) -> frozenset:
    """Slugs granted to a project, via its org's or its owner's enrollment."""
    if project is None:
        return frozenset()

    from beta.models import OrgBetaEnrollment, UserBetaEnrollment

    granted = frozenset()
    if project.org_id:
        org_enrollment = OrgBetaEnrollment.objects.filter(org_id=project.org_id).first()
        granted |= _slugs_for_enrollment(org_enrollment, registry)
    if project.owner_id:
        owner_enrollment = UserBetaEnrollment.objects.filter(user_id=project.owner_id).first()
        granted |= _slugs_for_enrollment(owner_enrollment, registry)
    return granted


def _user_granted_slugs(user, registry: dict) -> frozenset:
    """Slugs granted to a user by their personal enrollment."""
    if not user or not getattr(user, 'is_authenticated', False):
        return frozenset()

    from beta.models import UserBetaEnrollment

    enrollment = UserBetaEnrollment.objects.filter(user=user).first()
    return _slugs_for_enrollment(enrollment, registry)


def granted_slugs(user, project=None) -> frozenset:
    """
    Every feature slug available in this context — stable features plus anything
    granted by the project's or the user's enrollment.
    """
    registry = get_feature_registry()
    stable = frozenset(s for s, meta in registry.items() if meta['status'] == 'stable')
    return (
        stable
        | _project_granted_slugs(project, registry)
        | _user_granted_slugs(user, registry)
    )


def project_has_feature(project, feature_slug: str) -> bool:
    """
    True if the project context has the feature enabled (via org enrollment or
    owner enrollment). Used for anonymous public portal views and backend
    processes, where there is no request user.
    """
    if not project:
        return False
    try:
        registry = get_feature_registry()
        meta = registry.get(feature_slug)
        if meta is None:
            return False
        if meta['status'] == 'stable':
            return True
        return feature_slug in _project_granted_slugs(project, registry)
    except Exception:
        logger.exception("Error in project_has_feature(project=%s, slug=%s)", project, feature_slug)
        return False


def user_has_feature(user, feature_slug: str, project=None) -> bool:
    """
    Returns True if the user/context can access the named feature.

    Rules:
      - stable features → always True (everyone, no enrollment needed)
      - beta features:
          1. project is provided AND has project_has_feature → True
          2. User has a personal UserBetaEnrollment covering it → True
          3. Otherwise → False

    Args:
        user:         The request.user (can be anonymous/None).
        feature_slug: The BetaFeature slug string, e.g. 'custom_report_forms'.
        project:      Optional Project instance. Used to check project-level enrollment.
    """
    try:
        registry = get_feature_registry()
        meta = registry.get(feature_slug)
        if meta is None:
            return False
        if meta['status'] == 'stable':
            return True
        return feature_slug in granted_slugs(user, project)
    except Exception:
        logger.exception("Error in user_has_feature(user=%s, slug=%s)", user, feature_slug)
        return False


def get_user_beta_features(user, project=None) -> dict:
    """
    Returns a dict of {slug: bool} for all enrollable features.
    Used by the context processor to expose `beta_features` to every template.

    Example return value:
        {
            'custom_report_forms': True,
            'portal_custom_styling': False,
            'rest_api': True,
        }
    """
    try:
        registry = get_feature_registry()
        available = granted_slugs(user, project)
        return {
            slug: (meta['status'] == 'stable' or slug in available)
            for slug, meta in registry.items()
            if meta['is_enrollable']
        }
    except Exception:
        logger.exception("Error in get_user_beta_features(user=%s)", user)
        return {}
