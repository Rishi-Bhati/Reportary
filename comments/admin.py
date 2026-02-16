from django.contrib import admin
from .models import Comment

class CommentAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    list_display = ('__str__', 'commented_by', 'report', 'created_at')
    fieldsets = (
        (None, {'fields': ('uuid', 'report', 'commented_by', 'text')}),
        ('Additional info', {'fields': ('visibility', 'is_edited', 'created_at', 'updated_at')}),
    )
    search_fields = ('text', 'commented_by__username', 'report__title')

admin.site.register(Comment, CommentAdmin)