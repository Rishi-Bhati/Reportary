from django.contrib import admin
from beta.models import BetaFeature, UserBetaEnrollment, OrgBetaEnrollment


@admin.register(BetaFeature)
class BetaFeatureAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'status', 'is_enrollable', 'created_at')
    list_filter = ('status', 'is_enrollable')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('status', 'is_enrollable')
    ordering = ('name',)


@admin.register(UserBetaEnrollment)
class UserBetaEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'enrolled_at', 'feature_count')
    search_fields = ('user__username', 'user__email')
    filter_horizontal = ('features',)

    def feature_count(self, obj):
        count = obj.features.count()
        return count if count else 'All features'
    feature_count.short_description = 'Features'


@admin.register(OrgBetaEnrollment)
class OrgBetaEnrollmentAdmin(admin.ModelAdmin):
    list_display = ('org', 'enrolled_by', 'enrolled_at', 'feature_count')
    search_fields = ('org__name',)
    filter_horizontal = ('features',)

    def feature_count(self, obj):
        count = obj.features.count()
        return count if count else 'All features'
    feature_count.short_description = 'Features'
