from django.contrib import admin
from .models import Notification
from notifications.models import Invitation


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'actor', 'notification_type', 'title', 'is_read', 'requires_action', 'created_at')
    list_filter = ('notification_type', 'is_read', 'requires_action', 'created_at')
    search_fields = ('recipient__email', 'actor__email', 'title', 'message')
    readonly_fields = ('uuid', 'created_at')
    ordering = ('-created_at',)


@admin.register(Invitation)
class InvitationAdmin(admin.ModelAdmin):
    list_display = ('invited_user', 'invited_by', 'invite_type', 'status', 'created_at')
    list_filter = ('invite_type', 'status', 'created_at')
    search_fields = ('invited_user__email', 'invited_by__email')
    readonly_fields = ('uuid', 'created_at')
    ordering = ('-created_at',)
