from django.contrib import admin
from .models import  Component

class ComponentAdmin(admin.ModelAdmin):
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    list_display = ('uuid', 'name', 'project', 'created_at')
    fieldsets = (
        (None, {'fields': ('uuid', 'name', 'project', 'description')}),
        ('Additional info', {'fields': ('created_at', 'updated_at')}),
    )
    search_fields = ('name', 'project__title')

admin.site.register(Component, ComponentAdmin)