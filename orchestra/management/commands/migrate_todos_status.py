from django.core.management.base import BaseCommand

from orchestra.models import Todo

import logging
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = ('Migrates completion and skipped_datetime'
            ' values to status field in Todo model.')

    def add_arguments(self, parser):
        parser.add_argument(
            '--batch-size',
            help='Number of todos to be bulk updated.',
            action='store',
            type=int,
            default=10000)

    def chunked_queryset(self, queryset, chunk_size):
        start_pk = 0
        queryset = queryset.order_by('pk')

        while True:
            # No entry left
            if not queryset.filter(pk__gt=start_pk).exists():
                break

            try:
                # Fetch chunk_size entries if possible
                end_pk = queryset.filter(pk__gt=start_pk).values_list(
                    'pk', flat=True)[chunk_size - 1]

                # Fetch rest entries if less than chunk_size left
            except IndexError:
                end_pk = queryset.values_list('pk', flat=True).last()

            yield queryset.filter(pk__gt=start_pk).filter(pk__lte=end_pk)

            start_pk = end_pk

    def bulk_update_todo_status(self, queryset, status, batch_size):
        num_rows = queryset.count()
        logger.info('Started updating {} todos with status = {}'.format(
            num_rows, status))
        for chunk in self.chunked_queryset(queryset, batch_size):
            chunk.only('id', 'status').update(status=status)
        logger.info('Finished updating {} todos with status = {}'.format(
            num_rows, status))

    def handle(self, *args, **options):
        batch_size = options['batch_size']
        # declined todos
        self.bulk_update_todo_status(
            queryset=Todo.objects.filter(
                skipped_datetime__isnull=False),
            status=Todo.Status.DECLINED.value,
            batch_size=batch_size
        )
        # completed todos
        self.bulk_update_todo_status(
            queryset=Todo.objects.filter(
                skipped_datetime__isnull=True,
                completed=True),
            status=Todo.Status.COMPLETED.value,
            batch_size=batch_size
        )
        # pending todos
        self.bulk_update_todo_status(
            queryset=Todo.objects.filter(
                skipped_datetime__isnull=True,
                completed=False),
            status=Todo.Status.PENDING.value,
            batch_size=batch_size
        )
