from django.contrib import admin
from .models import Organisation

# Register your models here.
@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "domain", "verified", "created_at")
    search_fields = ("name", "owner__username", "domain")
    list_filter = ("verified", "created_at")
    readonly_fields = ("created_at", "uuid")
    filter_horizontal = ('members',)
    ordering = ("-created_at",)
    fieldsets = (
        (None, {'fields': ('uuid', 'name', 'domain', 'verified' )}),
        ('Details', {'fields': ('owner', 'members')}),
        ('Timestamps', {'fields': ('created_at',)}),
    )