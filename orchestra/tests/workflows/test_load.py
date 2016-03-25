import json
import os

from django.db import transaction
from django.test import modify_settings

from orchestra.core.errors import WorkflowError
from orchestra.models import Workflow
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.workflow import assert_test_dir_workflow_not_loaded  # noqa
from orchestra.tests.helpers.workflow import assert_test_dir_workflow_loaded
from orchestra.tests.helpers.workflow import assert_test_dir_v1_not_loaded
from orchestra.tests.helpers.workflow import assert_test_dir_v1_loaded
from orchestra.tests.helpers.workflow import assert_test_dir_v2_not_loaded
from orchestra.tests.helpers.workflow import assert_test_dir_v2_loaded
from orchestra.workflow.load import load_workflow
from orchestra.workflow.load import load_workflow_version


TEST_WORKFLOWS_MODULE = 'orchestra.tests.workflows'
TEST_WORKFLOWS_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '../workflows'))
WORKFLOWS = {
    'bad_certifications': {
        'dir': os.path.join(TEST_WORKFLOWS_DIR, 'bad_certification_dir'),
        'app_label': 'bad_certification_dir',
    },
    'valid': {
        'dir': os.path.join(TEST_WORKFLOWS_DIR, 'test_dir'),
        'app_label': 'test_dir',
    }
}
WORKFLOW_MODULES = [
    '{}.{}'.format(TEST_WORKFLOWS_MODULE, workflow_dict['app_label'])
    for workflow_dict in WORKFLOWS.values()
]
INVALID_VERSION = 'INVALID'
VERSION_1 = 'test_v1'
VERSION_2 = 'test_v2'


@modify_settings(INSTALLED_APPS={
    'append': WORKFLOW_MODULES,
})
class LoadWorkflowTestCase(OrchestraTestCase):

    def test_load_workflow(self):
        """ Ensure that a workflow directory loads correctly. """
        # Verify initial DB state.
        assert_test_dir_workflow_not_loaded(self)
        assert_test_dir_v1_not_loaded(self)
        assert_test_dir_v2_not_loaded(self)

        # Shouldn't be able to parse a workflow with nonexistent
        # certification dependencies.
        with self.assertRaisesMessage(
                WorkflowError,
                'Certification certification1 requires non-existent '
                'certification'):
            load_workflow(WORKFLOWS['bad_certifications']['app_label'],
                          VERSION_1)

        # Shouldn't be able to load a non-existent version.
        version_error = 'Invalid version requested: {}'.format(
            INVALID_VERSION)
        with self.assertRaisesMessage(WorkflowError, version_error):
            load_workflow(WORKFLOWS['valid']['app_label'], INVALID_VERSION)

        # Loading a version should create the right database objects.
        load_workflow(WORKFLOWS['valid']['app_label'], VERSION_1)
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)
        assert_test_dir_v2_not_loaded(self)

        # Loading a second version should create the right database objects.
        load_workflow(WORKFLOWS['valid']['app_label'], VERSION_2)
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)
        assert_test_dir_v2_loaded(self)

        # Reloading a version without --force should fail.
        force_error = 'Version {} already exists'.format(VERSION_1)
        with self.assertRaisesMessage(WorkflowError, force_error):
            load_workflow(WORKFLOWS['valid']['app_label'], VERSION_1)

        # Reloading versions with --force should succeed.
        load_workflow(WORKFLOWS['valid']['app_label'], VERSION_1, force=True)
        load_workflow(WORKFLOWS['valid']['app_label'], VERSION_2, force=True)
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)
        assert_test_dir_v2_loaded(self)

    def test_load_workflow_version(self):
        """ Ensure that workflow version loading works as desired. """
        # Verify initial DB state.
        assert_test_dir_workflow_not_loaded(self)
        assert_test_dir_v1_not_loaded(self)
        assert_test_dir_v2_not_loaded(self)

        # Load V1 of the workflow.
        load_workflow(WORKFLOWS['valid']['app_label'], VERSION_1)
        workflow = Workflow.objects.get(slug='test_dir')
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)
        assert_test_dir_v2_not_loaded(self)

        # Load the JSON data for the versions.
        v1_file_path = os.path.join(WORKFLOWS['valid']['dir'],
                                    'v1/version.json')
        with open(v1_file_path, 'r') as v1_file:
            v1_data = json.load(v1_file)

        v2_file_path = os.path.join(WORKFLOWS['valid']['dir'],
                                    'v2/version.json')
        with open(v2_file_path, 'r') as v2_file:
            v2_data = json.load(v2_file)

        # Without --force, can't overwrite a version.
        # We wrap calls to load_workflow_version in transaction.atomic, because
        # the call might create corrupt database state otherwise.
        force_error = 'Version {} already exists'.format(VERSION_1)
        with self.assertRaisesMessage(WorkflowError, force_error):
            with transaction.atomic():
                load_workflow_version(v1_data, workflow)

        # Even with --force, can't overwrite a version with a new step
        v1_data['steps'].append({'slug': 'invalid_new_step'})
        step_change_err_msg = ('Even with --force, cannot change the steps of '
                               'a workflow.')
        with self.assertRaisesMessage(WorkflowError, step_change_err_msg):
            with transaction.atomic():
                load_workflow_version(v1_data, workflow, force=True)
        v1_data['steps'] = v1_data['steps'][:-1]

        # Even with --force, can't change a step's creation dependencies.
        step_2_create_dependencies = v1_data['steps'][1]['creation_depends_on']
        step_2_create_dependencies.append('s3')
        topology_change_err_msg = ('Even with --force, cannot change the '
                                   'topology of a workflow.')
        with self.assertRaisesMessage(WorkflowError, topology_change_err_msg):
            with transaction.atomic():
                load_workflow_version(v1_data, workflow, force=True)
        v1_data['steps'][1]['creation_depends_on'] = (
            step_2_create_dependencies[:-1])

        # Even with --force, can't change a step's submission dependencies.
        step_3_submit_dependencies = v1_data['steps'][2][
            'submission_depends_on']
        step_3_submit_dependencies.append('s1')
        with self.assertRaisesMessage(WorkflowError, topology_change_err_msg):
            with transaction.atomic():
                load_workflow_version(v1_data, workflow, force=True)
        v1_data['steps'][2]['submission_depends_on'] = (
            step_3_submit_dependencies[:-1])

        # Otherwise, --force should reload versions correctly.
        with transaction.atomic():
            load_workflow_version(v1_data, workflow, force=True)
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)
        assert_test_dir_v2_not_loaded(self)

        # New versions with bad slugs should not load correctly
        v2_step_2 = v2_data['steps'][1]
        v2_step_2_create_dependencies = v2_step_2['creation_depends_on']
        v2_step_2_create_dependencies.append('not_a_real_step')
        bad_slug_error = '{}.{} contains a non-existent slug'
        with self.assertRaisesMessage(
                WorkflowError,
                bad_slug_error.format('s2', 'creation_depends_on')):
            with transaction.atomic():
                load_workflow_version(v2_data, workflow)
        v2_step_2['creation_depends_on'] = (
            v2_step_2_create_dependencies[:-1])

        v2_step_2_submit_dependencies = v2_step_2['submission_depends_on']
        v2_step_2_submit_dependencies.append('not_a_real_step')
        with self.assertRaisesMessage(
                WorkflowError,
                bad_slug_error.format('s2', 'submission_depends_on')):
            with transaction.atomic():
                load_workflow_version(v2_data, workflow)
        v2_step_2['submission_depends_on'] = (
            v2_step_2_submit_dependencies[:-1])

        v2_step_2_certification_dependencies = v2_step_2[
            'required_certifications']
        v2_step_2_certification_dependencies.append('not_a_real_certification')
        with self.assertRaisesMessage(
                WorkflowError,
                bad_slug_error.format('s2', 'required_certifications')):
            with transaction.atomic():
                load_workflow_version(v2_data, workflow)
        v2_step_2['required_certifications'] = (
            v2_step_2_certification_dependencies[:-1])

        # Otherwise, new versions should load correctly
        with transaction.atomic():
            load_workflow_version(v2_data, workflow)
        assert_test_dir_workflow_loaded(self)
        assert_test_dir_v1_loaded(self)
        assert_test_dir_v2_loaded(self)
