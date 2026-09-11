"""
Repair any Project rows where `public` and `visibility` disagree.

They were kept in step by ProjectForm.save() alone, so any row written by
another path could drift — with `visibility='private'` while `public=True`
still put it in public list views.
"""
from django.db import migrations
from django.db.models import Q


def sync_public_flag(apps, schema_editor):
    Project = apps.get_model('projects', 'Project')
    Project.objects.filter(visibility='public', public=False).update(public=True)
    Project.objects.filter(~Q(visibility='public'), public=True).update(public=False)


class Migration(migrations.Migration):
    dependencies = [('projects', '0012_reportformconfig')]
    operations = [migrations.RunPython(sync_public_flag, migrations.RunPython.noop)]
