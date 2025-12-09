from django.contrib import admin
from .models import Report
from comments.models import Comment

# This class defines an inline admin view for the Comment model.
# 'TabularInline' provides a compact, table-based layout for displaying related objects.
class CommentInline(admin.TabularInline):
    # The model to be displayed inline.
    model = Comment
    # The fields to display for each comment in the admin.
    fields = ('commented_by', 'text', 'visibility')
    # 'extra' controls how many empty forms for new comments are displayed.
    extra = 1
    # Allows administrators to delete comments from within the report admin page.
    can_delete = True


# This class customizes the admin interface for the Report model.
class ReportAdmin(admin.ModelAdmin):
    # 'list_display' defines the fields shown in the report list view in the admin.
    list_display = ('title', 'project', 'component', 'reported_by', 'description', 'steps', 'frequency', 'impact', 'severity', 'attatchment', 'visibility', 'created_at', 'comments_count')
    
    # 'search_fields' enables a search box for searching reports by title and description.
    search_fields = ('title', 'description')
    
    # 'readonly_fields' makes these fields non-editable in the admin.
    readonly_fields = ('created_at', 'updated_at')
    
    # 'inlines' includes the CommentInline, allowing admins to view, add, edit, and delete comments
    # directly on the report's change page.
    inlines = [CommentInline]
    
    # This is a custom method to display the number of comments for each report in the 'list_display'.
    def comments_count(self, obj):
        # 'obj' is the Report instance.
        # We use 'obj.comments.count()' to get the number of associated comments.
        # This works because of the 'related_name="comments"' we set on the ForeignKey in the Comment model.
        # The previous code used 'obj.comment_set.count()', which is the default and would fail if 'related_name' is set.
        return obj.comments.count()
    
    # This sets the column header for our custom method in the admin list view.
    comments_count.short_description = 'Comments'


# This line registers the Report model with the admin site, using the custom ReportAdmin options.
admin.site.register(Report, ReportAdmin)
