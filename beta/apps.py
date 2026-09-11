from django.apps import AppConfig


class BetaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'beta'
    verbose_name = 'Beta Program'

    def ready(self):
        from django.db.models.signals import post_delete, post_save

        from beta.models import BetaFeature
        from beta.utils import invalidate_feature_registry

        post_save.connect(invalidate_feature_registry, sender=BetaFeature,
                          dispatch_uid='beta_registry_invalidate_save')
        post_delete.connect(invalidate_feature_registry, sender=BetaFeature,
                            dispatch_uid='beta_registry_invalidate_delete')
