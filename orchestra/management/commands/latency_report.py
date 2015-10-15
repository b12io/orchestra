"""
Display a project latency report.

TODO(marcua): Fill the script in.  It's currently a dummy placeholder
with dummy placeholder arguments.
"""

from django.core.management.base import BaseCommand
from orchestra.analytics.latency import work_time_df
from orchestra.models import Project


import logging
logger = logging.getLogger(__name__)


def main(options):
    print(work_time_df(Project.objects.filter(id=1)))


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--remove-fake',
                            action='store_true',
                            dest='remove_fake',
                            default=False,
                            help='Remove all fake projects and tasks')

    def handle(self, *args, **options):
        main(options)
