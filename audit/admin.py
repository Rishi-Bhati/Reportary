from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('entity_type', 'entity_id', 'action', 'actor', 'field_name', 'created_at')
    list_filter = ('entity_type', 'action', 'created_at')
    search_fields = ('entity_type', 'entity_id', 'actor__email', 'field_name')
    readonly_fields = ('entity_type', 'entity_id', 'action', 'actor', 'field_name', 'old_value', 'new_value',
                       'parent_type', 'parent_id', 'created_at')
    ordering = ('-created_at',)

    def has_add_permission(self, request):
        return False  # AuditLogs are system-generated, not manually added

    def has_change_permission(self, request, obj=None):
        return False  # Audit logs are immutable