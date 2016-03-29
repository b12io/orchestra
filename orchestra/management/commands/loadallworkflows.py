from django.core.management.base import BaseCommand

from orchestra.core.errors import WorkflowError
from orchestra.workflow.load import get_workflow_version_slugs
from orchestra.workflow.load import load_workflow


class Command(BaseCommand):
    help = 'Loads a workflow version into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force', action='store_true', default=False,
            help=('If a workflow version already exists, update the existing '
                  'version instead of exiting.'))

    def handle(self, *args, **options):
        workflow_version_slugs = get_workflow_version_slugs()
        for workflow_slug, workflow_info in workflow_version_slugs.items():
            for version_slug in workflow_info['versions']:
                self.stdout.write('Loading {} {} from {}'.format(
                    workflow_slug, version_slug, workflow_info['app_label']))
                self._load_single_workflow(
                    workflow_info['app_label'], version_slug, options['force'])

    def _load_single_workflow(self, app_label, version_slug, force):
        try:
            load_workflow(app_label, version_slug, force=force)
        except WorkflowError as e:
            self.stderr.write(
                'An error occurred while loading the workflow: {}'
                .format(e))
