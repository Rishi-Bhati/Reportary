from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User

class UserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'name', 'type', 'is_active', 'is_staff', 'is_email_verified', 'date_joined', 'scheduled_deletion_date')
    list_filter = ('is_staff', 'is_active', 'type', 'is_email_verified')
    readonly_fields = ('uuid', 'date_joined', 'last_login')
    fieldsets = (
        (None, {'fields': ('uuid', 'email', 'password')}),
        ('Personal info', {'fields': ('name', 'username', 'type')}),
        ('Permissions', {'fields': ('is_staff', 'is_active', 'is_superuser', 'is_email_verified')}),
        ('Important dates', {'fields': ('last_login', 'date_joined', 'scheduled_deletion_date')}),
        ('Professional', {'fields': ('organisation', 'is_cp', 'business_email', 'cp_role')}),
        ('GitHub', {'fields': ('github_link', 'github_oauth_id', 'github_verified')}),
    )
    search_fields = ('email', 'username', 'name')
    ordering = ('-date_joined',)
    actions = ['reactivate_accounts']

    def reactivate_accounts(self, request, queryset):
        queryset.update(is_active=True, scheduled_deletion_date=None)
        self.message_user(request, f"{queryset.count()} account(s) reactivated.")
    reactivate_accounts.short_description = "Reactivate selected accounts"

admin.site.register(User, UserAdmin)