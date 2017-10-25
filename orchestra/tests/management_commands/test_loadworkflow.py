from io import StringIO

from django.core.management import call_command
from django.test import modify_settings

from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.workflow import assert_test_dir_v1_loaded
from orchestra.tests.helpers.workflow import assert_test_dir_v1_not_loaded
from orchestra.tests.helpers.workflow import assert_test_dir_v2_loaded
from orchestra.tests.helpers.workflow import assert_test_dir_v2_not_loaded
from orchestra.tests.helpers.workflow import assert_test_dir_workflow_loaded
from orchestra.tests.helpers.workflow import \
    assert_test_dir_workflow_not_loaded  # noqa

TEST_WORKFLOWS_MODULE = 'orchestra.tests.workflows'
VALID_WORKFLOW = 'test_dir'
VERSION_1 = 'test_v1'
VERSION_2 = 'test_v2'


@modify_settings(INSTALLED_APPS={
    'append': '{}.{}'.format(TEST_WORKFLOWS_MODULE, VALID_WORKFLOW)
})
class LoadWorkflowTestCase(OrchestraTestCase):

    def test_loadworkflow(self):
        """ Ensure that a workflow directory loads correctly. """
        # Verify initial DB state.
        assert_test_dir_workflow_not_loaded(self)
        assert_test_dir_v1_not_loaded(self)
        assert_test_dir_v2_not_loaded(self)

        # Loading a version should create the right database objects.
        call_command('loadworkflow', VALID_WORKFLOW, VERSION_1)
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)
        assert_test_dir_v2_not_loaded(self)

        # Loading a second version should create the right database objects.
        call_command('loadworkflow', VALID_WORKFLOW, VERSION_2)
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)
        assert_test_dir_v2_loaded(self)

        # Reloading a version without --force should fail.
        stderr = StringIO()
        call_command('loadworkflow', VALID_WORKFLOW, VERSION_1,
                     stderr=stderr)
        output = stderr.getvalue()
        error_preamble = 'An error occurred while loading the workflow'
        force_error = 'Version {} already exists'.format(VERSION_1)
        self.assertIn(error_preamble, output)
        self.assertIn(force_error, output)

        # Reloading a version with --force should succeed.
        stderr2 = StringIO()
        call_command('loadworkflow', VALID_WORKFLOW, VERSION_1, force=True,
                     stderr=stderr2)
        output2 = stderr2.getvalue()
        self.assertNotIn(error_preamble, output2)
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)
        assert_test_dir_v2_loaded(self)
