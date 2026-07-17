from django.contrib import admin
from public_portal.models import PublicReportingLink, AnonSubmission


@admin.register(PublicReportingLink)
class PublicReportingLinkAdmin(admin.ModelAdmin):
    list_display = ('project', 'is_active', 'allow_anonymous', 'created_at', 'regenerated_at')
    list_filter = ('is_active', 'allow_anonymous')
    search_fields = ('project__title', 'token')
    readonly_fields = ('token', 'created_at', 'regenerated_at', 'created_by')
    ordering = ('-created_at',)


@admin.register(AnonSubmission)
class AnonSubmissionAdmin(admin.ModelAdmin):
    list_display = ('link', 'submitted_at', 'report')
    list_filter = ('submitted_at',)
    readonly_fields = ('link', 'ip_hash', 'submitted_at', 'report')
    ordering = ('-submitted_at',)
