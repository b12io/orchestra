from django.core.management.base import BaseCommand
from orchestra.core.errors import WorkflowError
from orchestra.workflow.load import load_workflow


class Command(BaseCommand):
    help = 'Loads a workflow version into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            'app_label',
            help="The app label for the workflow's Django application.")
        parser.add_argument(
            'version_slug',
            help='The version of the workflow to load.')
        parser.add_argument(
            '--force', action='store_true', default=False,
            help=('If a workflow version already exists, update the existing '
                  'version instead of exiting.'))

    def handle(self, *args, **options):
        try:
            load_workflow(options['app_label'],
                          version_slug=options['version_slug'],
                          force=options['force'])
        except WorkflowError as e:
            self.stderr.write(
                'An error occurred while loading the workflow: {}'.format(e))
