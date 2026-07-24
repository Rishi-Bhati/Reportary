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

from restapi.auth import authenticate_api_request
from restapi.validators import validate_create_report, validation_error_response, ValidationError

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


def _create_report(request):
    """POST /api/v1/reports/ — create a report. Requires reports.create scope."""
    api_key, err = authenticate_api_request(request, resource='reports', action='create')
    if err:
        return err

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
        )

        # Notify project owner
        try:
            from notifications.services import create_notification
            create_notification(
                recipient=api_key.project.owner,
                actor=api_key.user,
                notification_type='new_report',
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


def _list_reports(request):
    """GET /api/v1/reports/ — list reports for the key's project. Requires reports.read scope."""
    api_key, err = authenticate_api_request(request, resource='reports', action='read')
    if err:
        return err

    try:
        from reports.models import Report
        reports_qs = Report.objects.filter(
            project=api_key.project
        ).select_related('component').order_by('-created_at')[:50]

        return JsonResponse(
            {'results': [_report_to_dict(r) for r in reports_qs]},
            status=200
        )
    except Exception:
        logger.exception("Error listing reports via API")
        return JsonResponse({'error': 'An internal error occurred.'}, status=500)


# ─── GET /api/v1/reports/<uuid>/ ─────────────────────────────────────────────

@csrf_exempt
def report_detail_endpoint(request, report_uuid):
    """GET /api/v1/reports/<uuid>/ — get a single report. Requires reports.read scope."""
    if request.method != 'GET':
        return JsonResponse({'error': 'Method not allowed.'}, status=405)

    api_key, err = authenticate_api_request(request, resource='reports', action='read')
    if err:
        return err

    try:
        from reports.models import Report
        try:
            report = Report.objects.select_related('component').get(
                uuid=report_uuid,
                project=api_key.project  # enforce project scope
            )
        except Report.DoesNotExist:
            return JsonResponse({'error': 'Report not found.'}, status=404)

        return JsonResponse(_report_to_dict(report), status=200)

    except Exception:
        logger.exception("Error fetching report via API")
        return JsonResponse({'error': 'An internal error occurred.'}, status=500)
