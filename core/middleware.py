import json
import logging
import requests as http_requests
from django.contrib import messages
from django.utils.deprecation import MiddlewareMixin
from django.utils.translation import get_language, activate
from django.conf import settings as django_settings

logger = logging.getLogger(__name__)

# Session key Django uses to store the explicitly chosen language
LANGUAGE_SESSION_KEY = '_language'


class GeoLanguageMiddleware(MiddlewareMixin):
    """
    Automatically activates Japanese for visitors from Japan, and uses the
    browser's Accept-Language header for device language detection.

    Priority order (highest → lowest):
      1. Explicit user choice (stored in session via set_language view)
      2. Browser/device language (Accept-Language header, handled by LocaleMiddleware)
      3. IP geolocation (this middleware — only fires when language is still 'en')

    Country detection strategy (no user prompt required):
      a. CDN headers: CF-IPCountry (Cloudflare), X-Country-Code, X-Geoip-Country
      b. ip-api.com free API (only called once per unique IP, cached 24h)

    Must be placed AFTER LocaleMiddleware in MIDDLEWARE.
    """

    def process_request(self, request):
        # 1. If user has already made an explicit language choice, respect it.
        if LANGUAGE_SESSION_KEY in request.session:
            return

        # 2. LocaleMiddleware already ran and may have activated 'ja' from
        #    the Accept-Language header. If so, nothing to do.
        current_lang = get_language() or 'en'
        if current_lang.startswith('ja'):
            return

        # 3. Try to determine the country from request headers / IP.
        country = self._get_country(request)
        if country == 'JP':
            activate('ja')
            # Store in session so subsequent requests are fast (no lookup needed)
            request.session[LANGUAGE_SESSION_KEY] = 'ja'

    # ── Country Detection ────────────────────────────────────────────────────

    def _get_country(self, request):
        """
        Returns the two-letter ISO country code (uppercase) or None.
        Tries cheap CDN headers first, then falls back to an IP API.
        """
        # a. Cloudflare adds CF-IPCountry on every request — zero latency.
        cf_country = request.META.get('HTTP_CF_IPCOUNTRY')
        if cf_country and cf_country not in ('XX', 'T1'):  # XX=unknown, T1=Tor
            return cf_country.upper()

        # b. Other CDNs / reverse proxies may set these.
        for header in ('HTTP_X_COUNTRY_CODE', 'HTTP_X_GEOIP_COUNTRY',
                       'HTTP_X_REAL_COUNTRY', 'HTTP_GEOIP_COUNTRY_CODE'):
            val = request.META.get(header)
            if val:
                return val.upper()[:2]

        # c. Fallback: call ip-api.com (free, no API key needed).
        #    Result is cached per-IP to avoid repeated calls.
        return self._lookup_ip_country(self._get_client_ip(request))

    def _get_client_ip(self, request):
        """Returns the real client IP, honouring X-Forwarded-For."""
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        if xff:
            return xff.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '')

    def _lookup_ip_country(self, ip):
        """
        Queries ip-api.com for the country code of the given IP.
        Uses Django's cache (default backend) with a 24-hour TTL so each
        unique IP is only looked up once per day.
        Returns a two-letter country code string, or None on failure.
        """
        if not ip or ip in ('127.0.0.1', '::1', 'testserver'):
            return None  # Local/test traffic — skip API call

        from django.core.cache import cache
        cache_key = f'geo_country_{ip}'
        cached = cache.get(cache_key)
        if cached is not None:
            return cached  # '' means "lookup was done, no result"

        try:
            resp = http_requests.get(
                f'http://ip-api.com/json/{ip}',
                params={'fields': 'status,countryCode'},
                timeout=1.5,   # Never block a page load for more than 1.5s
            )
            data = resp.json()
            country = data.get('countryCode', '') if data.get('status') == 'success' else ''
        except Exception as exc:
            logger.debug('GeoLanguageMiddleware: IP lookup failed for %s: %s', ip, exc)
            country = ''

        cache.set(cache_key, country, timeout=60 * 60 * 24)  # 24 hours
        return country or None


class HtmxMessageMiddleware(MiddlewareMixin):
    """
    Middleware that serializes Django messages to the 'HX-Trigger' header
    if the request is an HTMX request. This allows rendering Django messages
    as toast notifications dynamically for AJAX and partial page updates.
    """
    def process_response(self, request, response):
        if request.headers.get('HX-Request') == 'true' and not (300 <= response.status_code < 400):
            storage = messages.get_messages(request)
            django_messages = []
            for msg in storage:
                django_messages.append({
                    'text': msg.message,
                    'type': msg.tags if msg.tags else 'info'
                })
            
            if django_messages:
                hx_trigger = response.headers.get('HX-Trigger')
                try:
                    if hx_trigger:
                        trigger_data = json.loads(hx_trigger)
                    else:
                        trigger_data = {}
                except json.JSONDecodeError:
                    trigger_data = {hx_trigger: True} if hx_trigger else {}
                
                trigger_data['htmxMessages'] = django_messages
                response['HX-Trigger'] = json.dumps(trigger_data)
        
        return response
