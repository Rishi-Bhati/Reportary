"""
Prune old ApiRequestLog rows.

One row is written per authenticated API request, with three indexes and no
retention policy — the fastest-growing table in the schema. Run this on a cron
alongside purge_deleted_accounts.
"""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from restapi.models import ApiRequestLog

DEFAULT_RETENTION_DAYS = 90


class Command(BaseCommand):
    help = "Delete API request logs older than the retention window."

    def add_arguments(self, parser):
        parser.add_argument(
            '--days', type=int, default=DEFAULT_RETENTION_DAYS,
            help=f"Retention window in days (default: {DEFAULT_RETENTION_DAYS}).")
        parser.add_argument(
            '--dry-run', action='store_true',
            help="Report what would be deleted without deleting it.")

    def handle(self, *args, **options):
        days = options['days']
        if days < 1:
            self.stderr.write(self.style.ERROR("--days must be at least 1."))
            return

        cutoff = timezone.now() - timedelta(days=days)
        stale = ApiRequestLog.objects.filter(requested_at__lt=cutoff)
        count = stale.count()

        if options['dry_run']:
            self.stdout.write(
                f"[dry-run] {count} log(s) older than {days} days "
                f"(before {cutoff:%Y-%m-%d %H:%M} UTC) would be deleted.")
            return

        if not count:
            self.stdout.write("No API logs older than the retention window.")
            return

        stale.delete()
        self.stdout.write(self.style.SUCCESS(
            f"Deleted {count} API request log(s) older than {days} days."))
