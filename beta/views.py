"""
beta/views.py

HTMX-powered enrollment toggle endpoints.
All views are login_required and return HTML partials for HTMX.
"""
import logging
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import HttpResponse

from beta.models import BetaFeature, UserBetaEnrollment, OrgBetaEnrollment
from beta.utils import get_user_beta_features

logger = logging.getLogger(__name__)


# ─── User Enrollment ──────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def enroll_user(request):
    """Enroll the current user in the beta program (blanket enrollment)."""
    _, created = UserBetaEnrollment.objects.get_or_create(user=request.user)
    if created:
        logger.info("User %s enrolled in beta program", request.user.username)

    if request.headers.get('HX-Request'):
        return render(request, 'beta/partials/enrollment_status.html', {
            'enrolled': True,
            'beta_features': _get_enrollable_features(),
        })
    messages.success(request, "You've joined the Beta Program!")
    return redirect('accounts:settings')


@login_required
@require_http_methods(["POST"])
def unenroll_user(request):
    """Remove the current user from the beta program."""
    UserBetaEnrollment.objects.filter(user=request.user).delete()
    logger.info("User %s unenrolled from beta program", request.user.username)

    if request.headers.get('HX-Request'):
        return render(request, 'beta/partials/enrollment_status.html', {
            'enrolled': False,
            'beta_features': _get_enrollable_features(),
        })
    messages.info(request, "You've left the Beta Program.")
    return redirect('accounts:settings')


# ─── Org Enrollment ───────────────────────────────────────────────────────────

@login_required
@require_http_methods(["POST"])
def enroll_org(request, org_uuid):
    """Enroll an org in the beta program. Only org owner can do this."""
    from organisations.models import Organisation

    org = get_object_or_404(Organisation, uuid=org_uuid)
    if org.owner != request.user:
        return HttpResponse(status=403)

    enrollment, created = OrgBetaEnrollment.objects.get_or_create(
        org=org,
        defaults={'enrolled_by': request.user}
    )

    if created:
        logger.info("Org %s enrolled in beta program by %s", org.name, request.user.username)
        _notify_org_members_beta_enrolled(org, request.user)

    if request.headers.get('HX-Request'):
        return render(request, 'beta/partials/org_enrollment_status.html', {
            'org': org,
            'enrolled': True,
        })
    messages.success(request, f"{org.name} has joined the Beta Program!")
    return redirect('organisations:detail', uuid=org.uuid)


@login_required
@require_http_methods(["POST"])
def unenroll_org(request, org_uuid):
    """Remove an org from the beta program. Only org owner can do this."""
    from organisations.models import Organisation

    org = get_object_or_404(Organisation, uuid=org_uuid)
    if org.owner != request.user:
        return HttpResponse(status=403)

    OrgBetaEnrollment.objects.filter(org=org).delete()
    logger.info("Org %s unenrolled from beta program by %s", org.name, request.user.username)

    if request.headers.get('HX-Request'):
        return render(request, 'beta/partials/org_enrollment_status.html', {
            'org': org,
            'enrolled': False,
        })
    messages.info(request, f"{org.name} has left the Beta Program.")
    return redirect('organisations:detail', uuid=org.uuid)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _get_enrollable_features():
    return BetaFeature.objects.filter(is_enrollable=True, status='beta')


def _notify_org_members_beta_enrolled(org, actor):
    """Send in-app (not email) notifications to all org members."""
    try:
        from notifications.services import create_notification
        members = org.members.exclude(id=actor.id)
        for member in members:
            create_notification(
                recipient=member,
                actor=actor,
                notification_type='announcement',
                title=f"{org.name} joined the Beta Program",
                message=(
                    f"{org.name} has enabled beta features for all org projects. "
                    f"Want early access for your personal projects too? "
                    f"Head to Settings → Beta Program to enroll."
                ),
                target_content_type=None,
                target_uuid=None,
            )
    except Exception:
        logger.exception("Failed to notify org members about beta enrollment for org %s", org.pk)
