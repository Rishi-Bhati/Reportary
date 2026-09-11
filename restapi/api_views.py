"""
restapi/api_views.py

REST API endpoints. All endpoints:
  - Are CSRF-exempt (use API key auth instead)
  - Treat all incoming data as untrusted (goes through validators.py)
  - Return JSON exclusively
  - Log requests via auth.py

Endpoints:
    POST   /api/v1/reports/        → Submit a report  (scope: reports.create)
    GET    /api/v1/reports/        → List reports      (scope: reports.read)
    GET    /api/v1/reports/<uuid>/ → Get a report      (scope: reports.read)
"""
import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator

from restapi.auth import api_endpoint
from restapi.validators import (
    ValidationError,
    validate_create_report,
    validate_custom_fields,
    validation_error_response,
)

logger = logging.getLogger(__name__)


def _parse_json_body(request) -> tuple[dict, JsonResponse | None]:
    """Parse JSON body, return (data, None) or (None, error_response)."""
    content_type = request.META.get('CONTENT_TYPE', '')
    if 'application/json' not in content_type:
        return None, JsonResponse(
            {'error': "Content-Type must be application/json."},
            status=415
        )
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return None, JsonResponse({'error': "Invalid JSON body."}, status=400)
    if not isinstance(data, dict):
        return None, JsonResponse({'error': "Request body must be a JSON object."}, status=400)
    return data, None


def _report_to_dict(report) -> dict:
    """Serialize a Report instance to a safe dict for API responses."""
    return {
        'uuid': str(report.uuid),
        'title': report.title,
        'description': report.description,
        'steps': report.steps,
        'frequency': report.frequency,
        'impact': report.impact,
        'severity': report.severity,
        'status': report.status,
        'component': str(report.component.uuid) if report.component else None,
        'project': str(report.project.uuid),
        'report_type': report.report_type,
        'custom_fields': report.custom_fields_data,
        'created_at': report.created_at.isoformat(),
        'updated_at': report.updated_at.isoformat(),
    }


# ─── POST/GET /api/v1/reports/ ────────────────────────────────────────────────

@csrf_exempt
def reports_endpoint(request):
    """Route GET/POST to the appropriate handler."""
    if request.method == 'POST':
        return _create_report(request)
    elif request.method == 'GET':
        return _list_reports(request)
    return JsonResponse({'error': 'Method not allowed.'}, status=405)


@api_endpoint('reports', 'create')
def _create_report(request):
    """POST /api/v1/reports/ — create a report. Requires reports.create scope."""
    api_key = request.api_key

    data, err = _parse_json_body(request)
    if err:
        return err

    try:
        cleaned = validate_create_report(data)
    except ValidationError as e:
        return validation_error_response(e)

    try:
        from reports.models import Report
        from components.models import Component

        component = None
        component_uuid = cleaned.get('component_uuid')
        if component_uuid:
            try:
                component = Component.objects.get(
                    uuid=component_uuid,
                    project=api_key.project
                )
            except Component.DoesNotExist:
                return JsonResponse(
                    {'error': "Component not found in this project."},
                    status=404
                )

        # The submitted slug is resolved against the project's configured types.
        # It used to be written straight through, which both bypassed the
        # configured choice list and could overflow Report.report_type.
        from projects.models import ReportFormConfig, resolve_report_type_slug

        requested_type = cleaned.get('report_type')
        report_type_slug = resolve_report_type_slug(api_key.project, requested_type)
        if requested_type and requested_type != report_type_slug:
            return JsonResponse(
                {'error': f"'{requested_type}' is not a report type configured for this project."},
                status=400
            )

        # Validate custom fields against the schema if custom forms are active.
        from beta.utils import project_has_feature

        custom_fields_payload = cleaned.get('custom_fields', {})
        if project_has_feature(api_key.project, 'custom_report_forms'):
            form_config = ReportFormConfig.objects.filter(project=api_key.project).first()
            if form_config:
                type_config = form_config.get_fields_for_type(report_type_slug)
                custom_fields_schema = type_config.get('custom_fields', [])
                try:
                    custom_fields_payload = validate_custom_fields(
                        custom_fields_payload, custom_fields_schema, report_type_slug)
                except ValidationError as e:
                    return validation_error_response(e)
            else:
                custom_fields_payload = {}
        else:
            # No schema to validate against, so nothing is stored. Accepting an
            # arbitrary dict here meant unbounded JSON that the report detail
            # page then rendered under auto-generated labels.
            custom_fields_payload = {}

        if Report.objects.filter(project=api_key.project, title__iexact=cleaned['title']).exists():
            return JsonResponse(
                {'error': "A report with this title already exists for this project."},
                status=400
            )

        report = Report.objects.create(
            title=cleaned['title'],
            project=api_key.project,
            reported_by=api_key.user,
            description=cleaned['description'],
            steps=cleaned['steps'],
            frequency=cleaned['frequency'],
            impact=cleaned['impact'],
            component=component,
            status='open',
            visibility=True,
            report_type=report_type_slug,
            custom_fields_data=custom_fields_payload,
        )

        # Notify project owner
        try:
            from notifications.services import create_notification
            create_notification(
                recipient=api_key.project.owner,
                actor=api_key.user,
                notification_type='report_created',
                title="New Report via API",
                message=f"Report '{report.title}' was submitted to {api_key.project.title} via API.",
                target_content_type='report',
                target_uuid=report.uuid,
            )
        except Exception:
            pass  # Notification failure must not block the response

        return JsonResponse(_report_to_dict(report), status=201)

    except Exception:
        logger.exception("Error creating report via API key %s", api_key.public_key[:12])
        return JsonResponse({'error': 'An internal error occurred.'}, status=500)


DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100


@api_endpoint('reports', 'read')
def _list_reports(request):
    """
    GET /api/v1/reports/ — list reports for the key's project.
    Requires the reports.read scope.

    Paginated with `limit` and `offset`. This was a bare `[:50]` slice with no
    way to reach the rest, which made the endpoint unusable on any project of
    real size — and pagination is a contract, so it has to be settled before the
    feature leaves beta.
    """
    api_key = request.api_key

    try:
        limit = int(request.GET.get('limit', DEFAULT_PAGE_SIZE))
    except (TypeError, ValueError):
        return JsonResponse({'error': "'limit' must be an integer."}, status=400)
    try:
        offset = int(request.GET.get('offset', 0))
    except (TypeError, ValueError):
        return JsonResponse({'error': "'offset' must be an integer."}, status=400)

    if limit < 1 or limit > MAX_PAGE_SIZE:
        return JsonResponse(
            {'error': f"'limit' must be between 1 and {MAX_PAGE_SIZE}."}, status=400)
    if offset < 0:
        return JsonResponse({'error': "'offset' must not be negative."}, status=400)

    from reports.models import Report

    base_qs = Report.objects.filter(project=api_key.project)
    total = base_qs.count()
    page = base_qs.select_related('component').order_by('-created_at')[offset:offset + limit]

    return JsonResponse({
        'count': total,
        'limit': limit,
        'offset': offset,
        'results': [_report_to_dict(r) for r in page],
    }, status=200)


# ─── GET /api/v1/reports/<uuid>/ ─────────────────────────────────────────────

@csrf_exempt
def report_detail_endpoint(request, report_uuid):
    """GET /api/v1/reports/<uuid>/ — get a single report. Requires reports.read scope."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)
    return _report_detail(request, report_uuid)


@api_endpoint('reports', 'read')
def _report_detail(request, report_uuid):
    from reports.models import Report

    try:
        report = Report.objects.select_related('component').get(
            uuid=report_uuid,
            project=request.api_key.project,  # enforce project scope
        )
    except Report.DoesNotExist:
        return JsonResponse({'error': 'Report not found.'}, status=404)

    return JsonResponse(_report_to_dict(report), status=200)
