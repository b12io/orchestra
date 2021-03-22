from django.core.management.base import BaseCommand

from orchestra.models import Todo

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ('Migrates completion and skipped_datetime'
            ' values to status field in Todo model.')

    def bulk_update_todo_status(self, queryset, status):
        num_rows = queryset.count()
        logger.info('Started updating %s todos with status = %s',
                    num_rows, status)
        queryset.only('id', 'status').update(status=status)
        logger.info('Finished updating %s todos with status = %s',
                    num_rows, status)

    def handle(self, *args, **options):
        # declined todos
        self.bulk_update_todo_status(
            queryset=Todo.objects.filter(
                skipped_datetime__isnull=False),
            status=Todo.Status.DECLINED.value
        )
        # completed todos
        self.bulk_update_todo_status(
            queryset=Todo.objects.filter(
                skipped_datetime__isnull=True,
                completed=True),
            status=Todo.Status.COMPLETED.value
        )
        # pending todos
        self.bulk_update_todo_status(
            queryset=Todo.objects.filter(
                skipped_datetime__isnull=True,
                completed=False),
            status=Todo.Status.PENDING.value
        )
