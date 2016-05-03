from pydoc import locate

from django.core.management.base import BaseCommand
from django.db import transaction

from orchestra.models import Workflow
from orchestra.models import WorkflowVersion


LOAD_SCRIPT_MODULE = 'load_sample_data'


class Command(BaseCommand):
    help = ('Loads sample data for a workflow version into the database. '
            'Workflows must include a `{}.py` module in their top-level '
            'directory containing a `load(workflow_version)` function that '
            'loads sample data for the version. Otherwise, this command will '
            'do nothing.'.format(LOAD_SCRIPT_MODULE))

    def add_arguments(self, parser):
        parser.add_argument(
            'workflow_version',
            help=('The unique identifier of the workflow version (formatted '
                  'as <WORKFLOW_SLUG/VERSION_SLUG>).'))

    def handle(self, *args, **options):
        # Parse the version argument
        split_version = options['workflow_version'].split('/')
        if len(split_version) != 2:
            print('Please specify workflow versions in the format '
                  '"WORKFLOW_SLUG/WORKFLOW_VERSION".', file=self.stderr)
            return
        workflow_slug, version_slug = split_version

        # Verify that the workflow exists
        try:
            workflow = Workflow.objects.get(slug=workflow_slug)
        except Workflow.DoesNotExist:
            print('Workflow {} has not been loaded into the database. Please '
                  'load if before adding sample data.'
                  .format(workflow_slug),
                  file=self.stderr)
            return

        # Verify that the version exists
        try:
            version = workflow.versions.get(slug=version_slug)
        except WorkflowVersion.DoesNotExist:
            print('Version {} does not exist. Not loading sample data.'
                  .format(version_slug),
                  file=self.stderr)
            return

        # Import the load function and run it.
        load_function_dict = workflow.sample_data_load_function
        if not load_function_dict:
            print('Workflow {} does not provide sample data. Not loading '
                  'sample data.'.format(workflow_slug),
                  file=self.stderr)
            return

        try:
            load_function = locate(load_function_dict['path'])
            kwargs = load_function_dict.get('kwargs', {})
            with transaction.atomic():
                load_function(version, **kwargs)
            print('Successfully loaded sample data for {}'.format(version),
                  file=self.stdout)
        except Exception as e:
            print('An error occurred while loading sample data: {}'.format(e),
                  file=self.stderr)
