"""
restapi/dashboard_views.py

UI dashboard views for API key management and usage metrics.
These are standard Django views (not REST API endpoints) — they render HTML templates.

All views require login. API key operations also verify ownership.
"""
import secrets
import logging
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Avg, Q
from datetime import timedelta

from projects.models import Project
from restapi.models import ApiKey, ApiKeyScope, ApiRequestLog

logger = logging.getLogger(__name__)

# A person managing keys by hand does not need more than this, and an unbounded
# count is an easy way to inflate the key and log tables.
MAX_ACTIVE_KEYS_PER_USER = 25


def _projects_for_key_creation(user):
    """
    Projects a user may mint an API key for.

    Single source of truth for both the dashboard dropdown and create_key's
    validation, so the two cannot disagree about who has access.
    """
    from organisations.services import get_user_organisations
    from projects.models import Project

    return Project.objects.filter(
        Q(owner=user) |
        Q(project_head=user) |
        Q(collaborators=user) |
        Q(org__in=get_user_organisations(user))
    ).distinct().order_by('title')

# Scopes offered when creating a key. This must list only permissions that an
# endpoint actually honours: the UI previously advertised nine scopes across
# reports, comments and projects while /api/v1/ implemented two, so a user could
# mint a key granting `comments.create` and find nothing that accepted it.
# API scopes become a compatibility contract the moment the feature leaves beta,
# so extend this list as endpoints land, not before.
SCOPE_MATRIX = [
    ('reports', 'Reports', ['read', 'create']),
]

# Scopes that exist on old keys but are no longer offered. Shown as inactive in
# the UI rather than silently disappearing.
RETIRED_SCOPES = {
    ('reports', 'delete'),
    ('comments', 'read'), ('comments', 'create'), ('comments', 'delete'),
    ('projects', 'read'), ('projects', 'create'), ('projects', 'delete'),
}


def _daily_request_counts(logs_qs, days=14):
    """
    Requests per day for the last `days` days, as [{'date', 'count'}, …].

    One grouped query. Both dashboards previously issued one COUNT per day in a
    Python loop — and the org version re-evaluated an `api_key__in` subquery on
    every iteration.
    """
    from django.db.models.functions import TruncDate

    now = timezone.now()
    start = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0)

    counts = {
        row['day']: row['n']
        for row in logs_qs.filter(requested_at__gte=start)
                          .annotate(day=TruncDate('requested_at'))
                          .values('day')
                          .annotate(n=Count('id'))
    }

    out = []
    for offset in range(days - 1, -1, -1):
        day = (now - timedelta(days=offset)).date()
        out.append({'date': day.strftime('%b %d'), 'count': counts.get(day, 0)})
    return out


# ─── User API Dashboard ───────────────────────────────────────────────────────

@login_required
def user_dashboard(request):
    """Main API key management dashboard for the current user."""
    from beta.utils import user_has_feature
    if not user_has_feature(request.user, 'rest_api'):
        messages.warning(request, "REST API access requires Beta Program enrollment.")
        return redirect('home:settings')

    api_keys = ApiKey.objects.filter(
        user=request.user
    ).select_related('project').prefetch_related('scopes').order_by('-created_at')

    # High-level stats
    total_keys = api_keys.count()
    active_keys = sum(1 for k in api_keys if k.status == 'active')

    # Total requests in last 30 days
    since = timezone.now() - timedelta(days=30)
    total_requests = ApiRequestLog.objects.filter(
        api_key__user=request.user,
        requested_at__gte=since
    ).count()

    projects = _projects_for_key_creation(request.user)

    return render(request, 'restapi/dashboard.html', {
        'api_keys': api_keys,
        'projects': projects,
        'total_keys': total_keys,
        'active_keys': active_keys,
        'total_requests_30d': total_requests,
        'scope_matrix': SCOPE_MATRIX,
    })


@login_required
def key_detail(request, key_uuid):
    """Detail view for a single API key — shows usage metrics."""
    api_key = get_object_or_404(ApiKey, uuid=key_uuid, user=request.user)

    # ── Usage metrics ─────────────────────────────────────────────────────────
    now = timezone.now()
    since_24h = now - timedelta(hours=24)
    since_7d = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)

    logs_30d = ApiRequestLog.objects.filter(api_key=api_key, requested_at__gte=since_30d)

    total_30d = logs_30d.count()
    success_30d = logs_30d.filter(status_code__lt=400).count()
    error_30d = logs_30d.filter(status_code__gte=400).count()
    avg_response_ms = logs_30d.aggregate(avg=Avg('response_ms'))['avg']

    # Requests by day (last 14 days)
    daily_counts = _daily_request_counts(ApiRequestLog.objects.filter(api_key=api_key))

    # Status code breakdown
    status_breakdown = {}
    for log in logs_30d.values('status_code').annotate(count=Count('id')):
        status_breakdown[str(log['status_code'])] = log['count']

    # Recent logs (last 50)
    recent_logs = ApiRequestLog.objects.filter(
        api_key=api_key
    ).order_by('-requested_at')[:50]

    return render(request, 'restapi/key_detail.html', {
        'api_key': api_key,
        'scopes': api_key.scopes.all(),
        'scope_matrix': SCOPE_MATRIX,
        # Metrics
        'total_30d': total_30d,
        'success_30d': success_30d,
        'error_30d': error_30d,
        'avg_response_ms': round(avg_response_ms, 1) if avg_response_ms else None,
        'daily_counts': daily_counts,
        'status_breakdown': status_breakdown,
        'recent_logs': recent_logs,
    })


@login_required
@require_http_methods(["POST"])
def create_key(request):
    """Create a new API key. The raw secret is shown once and never stored."""
    from beta.utils import user_has_feature
    from projects.models import Project

    if not user_has_feature(request.user, 'rest_api'):
        return JsonResponse({'error': 'Beta enrollment required.'}, status=403)

    # Validate inputs
    name = request.POST.get('name', '').strip()
    project_uuid = request.POST.get('project_uuid', '').strip()
    expires_after_days = request.POST.get('expires_after_days', '').strip()
    selected_scopes = request.POST.getlist('scopes')  # list of 'reports.read', 'reports.create', etc.

    if not name or len(name) > 100:
        messages.error(request, "Key name is required (max 100 chars).")
        return redirect('restapi:dashboard')

    if not project_uuid:
        messages.error(request, "Please select a project.")
        return redirect('restapi:dashboard')

    # Verify user has access to this project. This used the owner/collaborator
    # pair while the dropdown above offered org projects too, so an org member
    # was shown a project and then told they had no access to it.
    from django.core.exceptions import ValidationError

    try:
        project = _projects_for_key_creation(request.user).get(uuid=project_uuid)
    except (Project.DoesNotExist, ValidationError, ValueError):
        # ValidationError covers a malformed uuid, which used to escape the
        # except clause and 500 the view.
        messages.error(request, "Project not found, or you don't have access to it.")
        return redirect('restapi:dashboard')

    # Parse expiry
    expires_at = None
    if expires_after_days:
        try:
            days = int(expires_after_days)
            if 1 <= days <= 365:
                expires_at = timezone.now() + timedelta(days=days)
        except ValueError:
            pass

    # Parse scopes
    valid_resources = {r for r, _, _ in SCOPE_MATRIX}
    valid_actions = {'read', 'create', 'delete'}
    scope_pairs = []
    for scope_str in selected_scopes:
        parts = scope_str.split('.', 1)
        if len(parts) == 2 and parts[0] in valid_resources and parts[1] in valid_actions:
            scope_pairs.append((parts[0], parts[1]))

    if not scope_pairs:
        messages.error(request, "Please select at least one permission scope.")
        return redirect('restapi:dashboard')

    if ApiKey.objects.filter(user=request.user, is_active=True).count() >= MAX_ACTIVE_KEYS_PER_USER:
        messages.error(
            request,
            f"You already have {MAX_ACTIVE_KEYS_PER_USER} active API keys. "
            f"Revoke one before creating another."
        )
        return redirect('restapi:dashboard')

    # Generate the raw secret (shown once, never stored)
    raw_secret = 'rsk_' + secrets.token_hex(32)
    hashed = ApiKey.hash_secret(raw_secret)

    api_key = ApiKey.objects.create(
        user=request.user,
        project=project,
        name=name,
        hashed_secret=hashed,
        expires_at=expires_at,
    )
    # Bulk create scopes
    ApiKeyScope.objects.bulk_create([
        ApiKeyScope(api_key=api_key, resource=res, action=act)
        for res, act in scope_pairs
    ])

    logger.info("API key created: %s by user %s for project %s",
                api_key.public_key[:12], request.user.username, project.uuid)

    # Render the key creation success page with the raw secret
    return render(request, 'restapi/key_created.html', {
        'api_key': api_key,
        'raw_secret': raw_secret,  # Shown once — never displayed again
        'full_token': f"{api_key.public_key}:{raw_secret}",
    })


@login_required
@require_http_methods(["POST"])
def revoke_key(request, key_uuid):
    """Revoke (deactivate) an API key."""
    api_key = get_object_or_404(ApiKey, uuid=key_uuid, user=request.user)
    api_key.is_active = False
    api_key.save(update_fields=['is_active'])
    logger.info("API key revoked: %s by user %s", api_key.public_key[:12], request.user.username)
    messages.success(request, f"API key '{api_key.name}' has been revoked.")

    if request.headers.get('HX-Request'):
        # The partial iterates as `key`, matching how dashboard.html includes it.
        return render(request, 'restapi/partials/key_row.html', {'key': api_key})
    return redirect('restapi:dashboard')


@login_required
@require_http_methods(["POST"])
def delete_key(request, key_uuid):
    """Permanently delete an API key and all its logs."""
    api_key = get_object_or_404(ApiKey, uuid=key_uuid, user=request.user)
    name = api_key.name
    api_key.delete()
    logger.info("API key deleted: %s by user %s", key_uuid, request.user.username)
    messages.success(request, f"API key '{name}' has been permanently deleted.")

    if request.headers.get('HX-Request'):
        # Empty body swaps the row out; the toast still arrives via HX-Trigger.
        from django.http import HttpResponse
        return HttpResponse('')
    return redirect('restapi:dashboard')


# ─── Org API Dashboard ────────────────────────────────────────────────────────

@login_required
def org_dashboard(request, org_uuid):
    """API dashboard for an org — shows all keys across all org projects."""
    from organisations.models import Organisation

    org = get_object_or_404(Organisation, uuid=org_uuid)
    if org.owner != request.user:
        messages.error(request, "Only the org owner can view the org API dashboard.")
        return redirect('organisations:details', uuid=org.uuid)

    from beta.utils import user_has_feature
    # Org dashboard requires org-level OR user-level beta enrollment
    if not user_has_feature(request.user, 'rest_api'):
        messages.warning(request, "REST API access requires Beta Program enrollment.")
        return redirect('home:settings')

    # Get all keys across org's projects
    from projects.models import Project
    org_projects = Project.objects.filter(org=org)
    api_keys = ApiKey.objects.filter(
        project__in=org_projects
    ).select_related('user', 'project').prefetch_related('scopes').order_by('-created_at')

    # Aggregate metrics
    since_30d = timezone.now() - timedelta(days=30)
    total_requests_30d = ApiRequestLog.objects.filter(
        api_key__in=api_keys,
        requested_at__gte=since_30d
    ).count()

    # Per-project key counts
    project_key_counts = (
        api_keys.values('project__title', 'project__uuid')
        .annotate(key_count=Count('id'))
        .order_by('-key_count')
    )

    # Requests per day for the org (last 14 days)
    org_daily_counts = _daily_request_counts(
        ApiRequestLog.objects.filter(api_key__project__in=org_projects))

    return render(request, 'restapi/org_dashboard.html', {
        'org': org,
        'api_keys': api_keys,
        'total_requests_30d': total_requests_30d,
        'project_key_counts': project_key_counts,
        'org_daily_counts': org_daily_counts,
        'active_key_count': sum(1 for k in api_keys if k.status == 'active'),
    })
