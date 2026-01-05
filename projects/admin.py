from django.contrib import admin
from .models import Project
from components.models import Component


class ComponentInline(admin.TabularInline): # Inline admin for components
    model = Component
    fields = ('name', 'description')
    extra = 1 # Number of extra forms to display
    can_delete = True


class ProjectAdmin(admin.ModelAdmin): # Admin for Project model
    list_display = ('title', 'owner', 'public', 'created_at', 'component_count')
    list_filter = ('public', 'created_at')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [ComponentInline]
    filter_horizontal = ('collaborators',)
    
    def component_count(self, obj):
        return obj.component_set.count()
    component_count.short_description = 'Components'


admin.site.register(Project, ProjectAdmin)