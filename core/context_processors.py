from django.utils import timezone
from django.utils.translation import get_language


def language_context(request):
    """Injects the current active language code into every template."""
    return {'current_language': get_language() or 'en'}


def announcements(request):
    """Injects active site announcements into every template context."""
    try:
        from core.models import Announcement
        now = timezone.now()
        active_announcements = Announcement.objects.filter(
            is_active=True
        ).filter(
            # Either no expiry set, or expiry hasn't passed yet
            expires_at__isnull=True
        ) | Announcement.objects.filter(
            is_active=True,
            expires_at__gt=now
        )
        active_announcements = active_announcements.distinct()
        if request.user.is_authenticated:
            active_announcements = active_announcements.exclude(
                dismissals__user=request.user
            )
        return {'site_announcements': active_announcements}
    except Exception:
        return {'site_announcements': []}
