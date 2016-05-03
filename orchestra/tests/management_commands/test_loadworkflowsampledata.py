from io import StringIO
import os
import sys

from django.core.management import call_command
from django.test import modify_settings

from orchestra.models import Workflow
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.workflow import assert_test_dir_v1_loaded
from orchestra.tests.helpers.workflow import assert_test_dir_workflow_loaded
from orchestra.workflow.load import load_workflow


NONEXISTENT_WORKFLOW_SLUG = 'DOESNOTEXIST'
TEST_WORKFLOWS_MODULE = 'orchestra.tests.workflows'
TEST_WORKFLOW = 'test_dir'
TEST_WORKFLOW_DIR = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    '../workflows/{}'.format(TEST_WORKFLOW)))

VERSION_1 = 'test_v1'
NONEXISTENT_VERSION = 'DOESNOTEXIST'


@modify_settings(INSTALLED_APPS={
    'append': '{}.{}'.format(TEST_WORKFLOWS_MODULE, TEST_WORKFLOW)
})
class LoadWorkflowSampleDataTestCase(OrchestraTestCase):

    def test_loadworkflowsampledata(self):
        """ Ensure that workflow sample data loads correctly. """

        # Load the test workflow
        load_workflow(TEST_WORKFLOW, VERSION_1)
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)

        # Calling the command with an invalid version argument should fail.
        invalid_args = (
            VERSION_1,  # Workflow slug omitted
            TEST_WORKFLOW,  # Version slug omitted
            '{}/{}/'.format(TEST_WORKFLOW, VERSION_1),  # Too many slashes
            '{}.{}'.format(TEST_WORKFLOW, VERSION_1),  # Wrong separator
        )
        for invalid_arg in invalid_args:
            invalid_stderr = StringIO()
            invalid_message = 'Please specify workflow versions in the format'
            call_command('loadworkflowsampledata', invalid_arg,
                         stderr=invalid_stderr)
            self.assertIn(invalid_message, invalid_stderr.getvalue())

        # Loading valid sample data should succeed without errors
        v1_str = '{}/{}'.format(TEST_WORKFLOW, VERSION_1)
        stdout = StringIO()
        call_command('loadworkflowsampledata', v1_str, stdout=stdout)
        output = stdout.getvalue()
        success_message = 'Successfully loaded sample data'
        self.assertIn(success_message, output)

        # clean up for subsequent commands
        del sys.modules['orchestra.tests.workflows.test_dir.load_sample_data']

        # Loading sample data for a nonexistent workflow should fail
        stderr1 = StringIO()
        call_command(
            'loadworkflowsampledata',
            '{}/{}'.format(NONEXISTENT_WORKFLOW_SLUG, VERSION_1),
            stderr=stderr1)
        output1 = stderr1.getvalue()
        no_workflow_error = ('Workflow {} has not been loaded into the '
                             'database'.format(NONEXISTENT_WORKFLOW_SLUG))
        self.assertIn(no_workflow_error, output1)

        # Loading sample data for a nonexistent version should fail
        stderr2 = StringIO()
        call_command(
            'loadworkflowsampledata',
            '{}/{}'.format(TEST_WORKFLOW, NONEXISTENT_VERSION),
            stderr=stderr2)
        output2 = stderr2.getvalue()
        no_version_error = ('Version {} does not exist'
                            .format(NONEXISTENT_VERSION))
        self.assertIn(no_version_error, output2)

        # Loading a workflow with no loading script should fail
        # Simulate this by moving the file.
        workflow = Workflow.objects.get(slug=TEST_WORKFLOW)
        workflow.sample_data_load_function = 'invalid_load_function'
        workflow.save()
        stderr3 = StringIO()
        call_command('loadworkflowsampledata', v1_str, stderr=stderr3)
        output3 = stderr3.getvalue()
        no_module_error = 'An error occurred while loading sample data'
        self.assertIn(no_module_error, output3)

        # Loading sample data for a workflow with no load function in its JSON
        # manifest should fail.
        workflow = Workflow.objects.get(slug=TEST_WORKFLOW)
        workflow.sample_data_load_function = None
        workflow.save()
        stderr4 = StringIO()
        call_command('loadworkflowsampledata', v1_str, stderr=stderr4)
        output4 = stderr4.getvalue()
        no_load_function_error = ('Workflow {} does not provide sample data'
                                  .format(TEST_WORKFLOW))
        self.assertIn(no_load_function_error, output4)
