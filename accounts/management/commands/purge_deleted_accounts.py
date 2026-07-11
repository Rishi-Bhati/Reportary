"""
Management command to permanently delete accounts that were soft-deleted
more than 30 days ago (scheduled_deletion_date has passed).

Usage:
    python manage.py purge_deleted_accounts

Recommended: Run daily via cron:
    0 2 * * * /path/to/venv/bin/python /path/to/manage.py purge_deleted_accounts
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import User


class Command(BaseCommand):
    help = 'Permanently delete accounts soft-deleted more than 30 days ago.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='List accounts to be deleted without actually deleting them.',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        due_for_deletion = User.objects.filter(
            is_active=False,
            scheduled_deletion_date__isnull=False,
            scheduled_deletion_date__lte=now,
        )

        count = due_for_deletion.count()
        if count == 0:
            self.stdout.write(self.style.SUCCESS('No accounts due for permanent deletion.'))
            return

        if options['dry_run']:
            self.stdout.write(self.style.WARNING(f'DRY RUN: {count} account(s) would be permanently deleted:'))
            for user in due_for_deletion:
                self.stdout.write(f'  - {user.email} (scheduled: {user.scheduled_deletion_date})')
        else:
            self.stdout.write(self.style.WARNING(f'Permanently deleting {count} account(s)...'))
            for user in due_for_deletion:
                email = user.email
                user.delete()
                self.stdout.write(f'  - Deleted: {email}')
            self.stdout.write(self.style.SUCCESS(f'Done. {count} account(s) permanently deleted.'))
