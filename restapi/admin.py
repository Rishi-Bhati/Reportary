from django.contrib import admin
from restapi.models import ApiKey, ApiKeyScope, ApiRequestLog


class ApiKeyScopeInline(admin.TabularInline):
    model = ApiKeyScope
    extra = 0


@admin.register(ApiKey)
class ApiKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'project', 'public_key_short', 'status',
                    'last_used_at', 'last_used_ip', 'expires_at', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'user__username', 'public_key')
    readonly_fields = ('public_key', 'hashed_secret', 'last_used_at', 'last_used_ip', 'created_at')
    inlines = [ApiKeyScopeInline]

    def public_key_short(self, obj):
        return obj.public_key[:16] + '...'
    public_key_short.short_description = 'Public Key'

    def status(self, obj):
        return obj.status
    status.short_description = 'Status'


@admin.register(ApiRequestLog)
class ApiRequestLogAdmin(admin.ModelAdmin):
    list_display = ('api_key', 'method', 'endpoint', 'status_code', 'response_ms',
                    'ip_address', 'requested_at')
    list_filter = ('method', 'status_code')
    search_fields = ('api_key__name', 'endpoint', 'ip_address')
    readonly_fields = ('api_key', 'method', 'endpoint', 'status_code',
                       'ip_address', 'response_ms', 'requested_at')
