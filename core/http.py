"""
Shared HTTP request helpers.

Client-IP extraction lived in three places with two different implementations:
public_portal took the rightmost X-Forwarded-For entry (correct — that hop is
added by the trusted proxy), while restapi and the geo middleware took the
leftmost, which is supplied by the client and trivially spoofed. That made
ApiKey.last_used_ip and every ApiRequestLog.ip_address attacker-chosen values
presented in a security dashboard as fact.
"""


def get_client_ip(request, default: str = '') -> str:
    """
    Return the client IP as reported by the trusted reverse proxy.

    Uses the RIGHTMOST X-Forwarded-For entry. The leftmost entries are whatever
    the client sent and must never be trusted for rate limiting or audit logs.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded:
        parts = [p.strip() for p in forwarded.split(',') if p.strip()]
        if parts:
            return parts[-1]
    return request.META.get('REMOTE_ADDR') or default
