from .services import get_unread_count

def notification_context(request):
    """Injects unread notification count into every template context."""
    if request.user.is_authenticated:
        return {
            'unread_notification_count': get_unread_count(request.user)
        }
    return {
        'unread_notification_count': 0
    }
