"""
restapi/auth.py

Authenticates incoming API requests.
ALL incoming data is treated as untrusted.

Authentication flow:
  1. Parse Authorization header: Bearer <public_key>:<secret_key>
  2. Look up ApiKey by public_key (DB hit, indexed)
  3. Verify key is active and not expired
  4. Constant-time PBKDF2 secret verification
  5. Check the required scope exists for this key
  6. Log last_used_at and last_used_ip
  7. Return (api_key, error_response) tuple

Usage:
    api_key, err = authenticate_api_request(request, resource='reports', action='create')
    if err:
        return err
"""
import logging
import time
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

logger = logging.getLogger(__name__)


class ApiAuthError(Exception):
    """Raised during API authentication failure."""
    def __init__(self, message: str, status: int = 401):
        self.message = message
        self.status = status
        super().__init__(message)


def _parse_auth_header(request) -> tuple[str, str]:
    """
    Parse 'Authorization: Bearer <public_key>:<secret_key>' header.
    Returns (public_key, secret_key) or raises ApiAuthError.
    """
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    if not auth_header.startswith('Bearer '):
        raise ApiAuthError("Missing or malformed Authorization header. Expected: Bearer <public_key>:<secret_key>")

    token = auth_header[len('Bearer '):]
    parts = token.split(':', 1)
    if len(parts) != 2:
        raise ApiAuthError("Invalid token format. Expected: Bearer <public_key>:<secret_key>")

    public_key, secret_key = parts[0].strip(), parts[1].strip()
    if not public_key or not secret_key:
        raise ApiAuthError("Public key or secret key is empty.")

    # Basic sanity checks — public keys always start with 'rpk_'
    if not public_key.startswith('rpk_'):
        raise ApiAuthError("Invalid public key format.")

    return public_key, secret_key


def _get_client_ip(request) -> str | None:
    """Extract client IP, respecting proxy headers."""
    x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded:
        return x_forwarded.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def authenticate_api_request(request, resource: str, action: str):
    """
    Full API authentication + authorization pipeline.

    Returns:
        (ApiKey instance, None)         on success
        (None, JsonResponse with error) on failure

    Args:
        request:  The Django HttpRequest.
        resource: The resource being accessed (e.g. 'reports').
        action:   The action being performed (e.g. 'create', 'read').
    """
    from restapi.models import ApiKey, ApiRequestLog

    start_time = time.monotonic()
    client_ip = _get_client_ip(request)

    def _log_and_error(message: str, status: int, api_key=None):
        logger.warning(
            "API auth failure: %s | ip=%s | resource=%s | action=%s",
            message, client_ip, resource, action
        )
        response = JsonResponse({'error': message}, status=status)
        # Log the failed attempt if we have a key
        if api_key:
            _record_request_log(api_key, request, status, start_time)
        return None, response

    # ── Step 1: Parse header ──────────────────────────────────────────────────
    try:
        public_key, raw_secret = _parse_auth_header(request)
    except ApiAuthError as e:
        return _log_and_error(e.message, e.status)

    # ── Step 2: Look up the API key ───────────────────────────────────────────
    try:
        api_key = ApiKey.objects.select_related('user', 'project').get(
            public_key=public_key
        )
    except ApiKey.DoesNotExist:
        # Do not reveal whether the key exists
        return _log_and_error("Invalid credentials.", 401)

    # ── Step 3: Check if key is usable ────────────────────────────────────────
    if not api_key.is_usable:
        return _log_and_error("This API key is revoked or expired.", 401, api_key)

    # ── Step 4: Verify secret (constant-time) ─────────────────────────────────
    if not api_key.verify_secret(raw_secret):
        return _log_and_error("Invalid credentials.", 401, api_key)

    # ── Step 5: Check scope ───────────────────────────────────────────────────
    has_scope = api_key.scopes.filter(resource=resource, action=action).exists()
    if not has_scope:
        return _log_and_error(
            f"This key does not have the '{resource}.{action}' permission.",
            403, api_key
        )

    # ── Step 6: Check beta enrollment (rest_api feature gate) ─────────────────
    from beta.utils import user_has_feature
    if not user_has_feature(api_key.user, 'rest_api', project=api_key.project):
        return _log_and_error(
            "REST API access requires Beta Program enrollment.",
            403, api_key
        )

    # ── Step 7: Update usage tracking ─────────────────────────────────────────
    ApiKey.objects.filter(pk=api_key.pk).update(
        last_used_at=timezone.now(),
        last_used_ip=client_ip,
    )

    # ── Step 8: Log the successful request ────────────────────────────────────
    _record_request_log(api_key, request, 200, start_time)  # placeholder — view updates status

    logger.info(
        "API auth success: key=%s user=%s project=%s resource=%s action=%s ip=%s",
        api_key.public_key[:12], api_key.user.username,
        api_key.project.uuid, resource, action, client_ip
    )
    return api_key, None


def _record_request_log(api_key, request, status_code: int, start_time: float):
    """Async-safe: fire-and-forget request log entry."""
    from restapi.models import ApiRequestLog
    try:
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        ApiRequestLog.objects.create(
            api_key=api_key,
            method=request.method,
            endpoint=request.path,
            status_code=status_code,
            ip_address=_get_client_ip(request),
            response_ms=elapsed_ms,
        )
    except Exception:
        logger.exception("Failed to write ApiRequestLog")
