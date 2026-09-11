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
    """Extract client IP. See core.http.get_client_ip for why it is the rightmost hop."""
    from core.http import get_client_ip

    return get_client_ip(request) or None


# ── Throttling ───────────────────────────────────────────────────────────────
# Fixed-window counters in the cache. Two separate limits:
#   * failed authentication attempts, keyed by public key + IP, to bound
#     brute-forcing of a secret;
#   * successful requests, keyed by public key, as a basic fair-use ceiling.
AUTH_FAILURE_LIMIT = 10
AUTH_FAILURE_WINDOW = 300      # seconds
REQUEST_LIMIT = 120
REQUEST_WINDOW = 60            # seconds


def _throttle(cache_key: str, limit: int, window: int) -> bool:
    """Increment a fixed-window counter. Returns True when over the limit."""
    from django.core.cache import cache

    try:
        # add() only succeeds on the first call in a window, which is what
        # starts the clock; incr() raises ValueError if the key expired between
        # the two calls, so fall back to re-seeding it.
        if cache.add(cache_key, 1, window):
            return False
        try:
            count = cache.incr(cache_key)
        except ValueError:
            cache.set(cache_key, 1, window)
            return False
        return count > limit
    except Exception:
        logger.exception("Throttle check failed for %s; allowing the request.", cache_key)
        return False


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
        """
        `api_key` is passed only once the caller has proven possession of the
        secret. Failures before that point are logged to the application log
        only — writing them to ApiRequestLog let anyone holding a (non-secret)
        public key grow the owner's table without limit.
        """
        logger.warning(
            "API auth failure: %s | ip=%s | resource=%s | action=%s",
            message, client_ip, resource, action
        )
        response = JsonResponse({'error': message}, status=status)
        if api_key:
            record_request_log(api_key, request, status, start_time)
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

    # ── Step 3: Throttle brute-force attempts ─────────────────────────────────
    failure_key = f'restapi:authfail:{public_key}:{client_ip}'
    from django.core.cache import cache
    if (cache.get(failure_key) or 0) > AUTH_FAILURE_LIMIT:
        return _log_and_error("Too many failed authentication attempts. Try again later.", 429)

    # ── Step 4: Check if key is usable ────────────────────────────────────────
    if not api_key.is_usable:
        return _log_and_error("This API key is revoked or expired.", 401)

    # ── Step 5: Verify secret (constant-time) ─────────────────────────────────
    if not api_key.verify_secret(raw_secret):
        _throttle(failure_key, AUTH_FAILURE_LIMIT, AUTH_FAILURE_WINDOW)
        return _log_and_error("Invalid credentials.", 401)

    # From here on the caller holds the secret, so failures are theirs to see
    # in the usage dashboard.

    # ── Step 6: Fair-use ceiling ──────────────────────────────────────────────
    if _throttle(f'restapi:rate:{public_key}', REQUEST_LIMIT, REQUEST_WINDOW):
        return _log_and_error(
            f"Rate limit exceeded ({REQUEST_LIMIT} requests per "
            f"{REQUEST_WINDOW} seconds).", 429, api_key
        )

    # ── Step 7: Check scope ───────────────────────────────────────────────────
    has_scope = api_key.scopes.filter(resource=resource, action=action).exists()
    if not has_scope:
        return _log_and_error(
            f"This key does not have the '{resource}.{action}' permission.",
            403, api_key
        )

    # ── Step 8: Check beta enrollment (rest_api feature gate) ─────────────────
    from beta.utils import user_has_feature
    if not user_has_feature(api_key.user, 'rest_api', project=api_key.project):
        return _log_and_error(
            "REST API access requires Beta Program enrollment.",
            403, api_key
        )

    # ── Step 9: Update usage tracking ─────────────────────────────────────────
    ApiKey.objects.filter(pk=api_key.pk).update(
        last_used_at=timezone.now(),
        last_used_ip=client_ip,
    )

    # NOTE: the request log is written by the api_endpoint decorator once the
    # view has produced a response, so it records the real status code. This
    # used to write a hardcoded 200 here with a "view updates status" comment;
    # no view ever did, so every metric on the usage dashboard was wrong.

    logger.info(
        "API auth success: key=%s user=%s project=%s resource=%s action=%s ip=%s",
        api_key.public_key[:12], api_key.user.username,
        api_key.project.uuid, resource, action, client_ip
    )
    return api_key, None


def record_request_log(api_key, request, status_code: int, start_time: float):
    """Write one usage-log row. Never raises."""
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


def api_endpoint(resource: str, action: str):
    """
    Authenticate, run the view, then log the request with its REAL status code.

    Wrapping the view is what makes the usage metrics truthful: authentication
    cannot know how the request ends, so logging there could only ever record a
    guess. `request.api_key` is set for the view's benefit.
    """
    from functools import wraps

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            start_time = time.monotonic()
            api_key, error = authenticate_api_request(request, resource=resource, action=action)
            if error:
                return error

            request.api_key = api_key
            try:
                response = view(request, *args, **kwargs)
            except Exception:
                logger.exception("Unhandled error in API endpoint %s", request.path)
                response = JsonResponse({'error': 'An internal error occurred.'}, status=500)

            record_request_log(api_key, request, response.status_code, start_time)
            return response

        return wrapper

    return decorator
