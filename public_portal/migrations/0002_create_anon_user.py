"""
Data migration: Create the anonymous system user used as reported_by
for all anonymous portal submissions.

This account is permanently inactive and cannot log in.
"""
from django.db import migrations


def create_anonymous_user(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    if not User.objects.filter(email='anonymous@reportary.internal').exists():
        User.objects.create(
            username='anonymous',
            email='anonymous@reportary.internal',
            is_active=False,
            is_staff=False,
            is_superuser=False,
            # Unusable password — cannot log in
            password='!anonymous_system_user_cannot_login',
        )


def reverse_anonymous_user(apps, schema_editor):
    # Only delete if no anonymous reports reference it
    User = apps.get_model('accounts', 'User')
    Report = apps.get_model('reports', 'Report')
    anon = User.objects.filter(email='anonymous@reportary.internal').first()
    if anon and not Report.objects.filter(reported_by=anon).exists():
        anon.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('reports', '0010_report_is_anonymous_report_submitted_via_link'),
    ]

    operations = [
        migrations.RunPython(create_anonymous_user, reverse_anonymous_user),
    ]
