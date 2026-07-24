from django.utils import timezone
from django.utils.translation import get_language
from django.db.models import Q


def language_context(request):
    """Injects the current active language code into every template."""
    return {'current_language': get_language() or 'en'}


def announcements(request):
    """Injects active site announcements into every template context."""
    try:
        from core.models import Announcement
        now = timezone.now()

        # Single query using Q objects avoids union issues with .exclude()
        qs = Announcement.objects.filter(
            is_active=True
        ).filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now)
        )

        if request.user.is_authenticated:
            qs = qs.exclude(dismissals__user=request.user)

        return {'site_announcements': qs}
    except Exception:
        return {'site_announcements': []}
