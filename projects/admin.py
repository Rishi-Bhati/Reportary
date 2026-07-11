from django.contrib import admin
from .models import Project, ProjectTask
from components.models import Component


class ComponentInline(admin.TabularInline): # Inline admin for components
    model = Component
    fields = ('name', 'description')
    extra = 1 # Number of extra forms to display
    can_delete = True


class ProjectTaskInline(admin.TabularInline):
    model = ProjectTask
    fields = ('title', 'is_completed', 'created_at')
    readonly_fields = ('created_at',)
    extra = 0
    can_delete = True


class ProjectAdmin(admin.ModelAdmin): # Admin for Project model
    list_display = ('title', 'owner', 'public', 'created_at', 'component_count')
    list_filter = ('public', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ComponentInline, ProjectTaskInline]
    filter_horizontal = ('collaborators',)
    
    def component_count(self, obj):
        return obj.project_components.count()
    component_count.short_description = 'Components'


admin.site.register(Project, ProjectAdmin)


@admin.register(ProjectTask)
class ProjectTaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'is_completed', 'created_at')
    list_filter = ('is_completed', 'created_at')
    search_fields = ('title', 'project__title')
    readonly_fields = ('created_at',)