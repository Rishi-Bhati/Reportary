from django.utils import timezone


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
        return {'site_announcements': active_announcements.distinct()}
    except Exception:
        return {'site_announcements': []}
