"""
beta/utils.py

The single gate for all beta feature access checks.
Use this function everywhere — views, forms, templates (via context_processors).

Usage:
    from beta.utils import user_has_feature

    if user_has_feature(request.user, 'custom_report_forms', project=project):
        # show beta feature
"""
import logging

logger = logging.getLogger(__name__)


def project_has_feature(project, feature_slug: str) -> bool:
    """
    Returns True if the project context has the feature enabled (via org enrollment or owner enrollment).
    Useful for anonymous public portal views or backend processes.
    """
    if not project:
        return False

    try:
        from beta.models import BetaFeature, UserBetaEnrollment, OrgBetaEnrollment

        feature = BetaFeature.objects.filter(slug=feature_slug).first()
        if not feature:
            return False

        if feature.status == 'stable':
            return True

        # Check org-level enrollment
        if project.org_id:
            org_enrollment = OrgBetaEnrollment.objects.filter(org_id=project.org_id).first()
            if org_enrollment:
                org_features = org_enrollment.features.all()
                if not org_features.exists() or org_features.filter(slug=feature_slug).exists():
                    return True

        # Check project owner enrollment
        if project.owner:
            owner_enrollment = UserBetaEnrollment.objects.filter(user=project.owner).first()
            if owner_enrollment:
                owner_features = owner_enrollment.features.all()
                if not owner_features.exists() or owner_features.filter(slug=feature_slug).exists():
                    return True

        return False
    except Exception:
        logger.exception("Error in project_has_feature(project=%s, slug=%s)", project, feature_slug)
        return False


def user_has_feature(user, feature_slug: str, project=None) -> bool:
    """
    Returns True if the user/context can access the named feature.

    Rules:
      - stable features → always True (everyone, no enrollment needed)
      - beta features:
          1. User has a personal UserBetaEnrollment for this feature → True
          2. project is provided AND has project_has_feature → True
          3. Otherwise → False

    Args:
        user:         The request.user (can be anonymous/None).
        feature_slug: The BetaFeature slug string, e.g. 'custom_report_forms'.
        project:      Optional Project instance. Used to check project-level enrollment.
    """
    try:
        from beta.models import BetaFeature, UserBetaEnrollment

        feature = BetaFeature.objects.filter(slug=feature_slug).first()
        if not feature:
            return False

        # Stable features are available to everyone
        if feature.status == 'stable':
            return True

        # ── Check project context first (if provided) ────────────────────────
        if project and project_has_feature(project, feature_slug):
            return True

        # ── Check personal user enrollment ──────────────────────────────────
        if user and user.is_authenticated:
            enrollment = UserBetaEnrollment.objects.filter(user=user).first()
            if enrollment:
                enrolled_features = enrollment.features.all()
                if not enrolled_features.exists():
                    return True
                if enrolled_features.filter(slug=feature_slug).exists():
                    return True

        return False

    except Exception:
        logger.exception("Error in user_has_feature(user=%s, slug=%s)", user, feature_slug)
        return False


def get_user_beta_features(user, project=None) -> dict:
    """
    Returns a dict of {slug: bool} for all enrollable beta features.
    Useful for passing to templates. Also used by the context processor.

    Example return value:
        {
            'custom_report_forms': True,
            'portal_custom_styling': False,
            'rest_api': True,
        }
    """
    try:
        from beta.models import BetaFeature
        features = BetaFeature.objects.filter(is_enrollable=True)
        return {f.slug: user_has_feature(user, f.slug, project=project) for f in features}
    except Exception:
        return {}
