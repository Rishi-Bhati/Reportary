from django.contrib import admin
from .models import Report
from comments.models import Comment
# Register your models here.


class CommentInline(admin.TabularInline): # Inline admin for components
    model = Comment
    fields = ('author', 'display_name', 'content')
    extra = 1 # Number of extra forms to display
    can_delete = True


class ReportAdmin(admin.ModelAdmin): # Admin for Project model
    list_display = ('title', 'project', 'component', 'reported_by', 'description', 'steps', 'frequency', 'impact', 'severity', 'attatchment', 'visibility', 'created_at', 'comments_count')
    # list_filter = ('public', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CommentInline]
    
    def comments_count(self, obj):
        return obj.comments.count()
    comments_count.short_description = 'Comments'


admin.site.register(Report, ReportAdmin)
