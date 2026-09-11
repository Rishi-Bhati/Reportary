"""
Reset PortalTheme rows that were created by accident.

configure_portal_theme called get_or_create() on GET, so merely opening the
theme editor wrote a row — and the model's defaults were a dark palette while
portal.html's no-theme fallback was light. Opening the editor and changing
nothing therefore flipped the live portal to dark.

This resets only rows that still hold the exact old defaults and carry no
customisation of their own, so a deliberately dark theme is left alone.
"""
from django.db import migrations

OLD_DEFAULTS = {
    'primary_color': '#6366f1',
    'background_color': '#0f0f1a',
    'card_background': '#1a1a2e',
    'text_color': '#e2e8f0',
    'accent_color': '#818cf8',
    'font_family': 'Inter',
    'border_radius': '12px',
}

NEW_DEFAULTS = {
    'primary_color': '#226ce0',
    'background_color': '#f8f6fa',
    'card_background': '#ffffff',
    'text_color': '#111827',
}


def reset_untouched_themes(apps, schema_editor):
    PortalTheme = apps.get_model('public_portal', 'PortalTheme')
    untouched = PortalTheme.objects.filter(**OLD_DEFAULTS).filter(
        custom_css__in=('', None),
        custom_logo_url__isnull=True,
        custom_heading__isnull=True,
    )
    untouched.update(**NEW_DEFAULTS)


def noop(apps, schema_editor):
    """Not reversible — we cannot tell which rows this migration changed."""


class Migration(migrations.Migration):
    dependencies = [
        ('public_portal', '0005_alter_portaltheme_background_color_and_more'),
    ]
    operations = [migrations.RunPython(reset_untouched_themes, noop)]
