# Generated manually to seed initial beta features

from django.db import migrations

def seed_beta_features(apps, schema_editor):
    BetaFeature = apps.get_model('beta', 'BetaFeature')
    
    features = [
        {
            'slug': 'custom_report_forms',
            'name': 'Custom Reporting Forms',
            'description': 'Allows projects and components to configure custom fields and customized frequency options for reporting.',
            'status': 'beta',
            'is_enrollable': True,
        },
        {
            'slug': 'portal_custom_styling',
            'name': 'Public Portal Custom Styling',
            'description': 'Configure custom visual styles and arbitrary CSS for your project\'s public report portal.',
            'status': 'beta',
            'is_enrollable': True,
        },
        {
            'slug': 'rest_api',
            'name': 'REST API & API Keys',
            'description': 'Generate API keys and use programmatic endpoints to submit or fetch reports directly.',
            'status': 'beta',
            'is_enrollable': True,
        },
    ]
    
    for f_data in features:
        BetaFeature.objects.get_or_create(
            slug=f_data['slug'],
            defaults={
                'name': f_data['name'],
                'description': f_data['description'],
                'status': f_data['status'],
                'is_enrollable': f_data['is_enrollable'],
            }
        )

def remove_beta_features(apps, schema_editor):
    BetaFeature = apps.get_model('beta', 'BetaFeature')
    BetaFeature.objects.filter(slug__in=['custom_report_forms', 'portal_custom_styling', 'rest_api']).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('beta', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_beta_features, remove_beta_features),
    ]
