import json
import os

from orchestra.core.errors import WorkflowError
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.workflow.directory import parse_workflow_directory


NONEXISTENT_DIR = '/foo/bar/baz/'
TEST_WORKFLOWS_DIR = os.path.abspath(os.path.dirname(__file__))
INVALID_WORKFLOW_DIR = os.path.join(TEST_WORKFLOWS_DIR, 'invalid_dir')
EMPTY_WORKFLOW_DIR = os.path.join(TEST_WORKFLOWS_DIR, 'no_version_dir')
VALID_WORKFLOW_DIR = os.path.join(TEST_WORKFLOWS_DIR, 'test_dir')


class WorkflowDirectoryTestCase(OrchestraTestCase):

    def test_parse_workflow_directory(self):
        """ Ensure that workflow version directories are parsed correctly. """

        # Shouldn't be able to parse a non-existent directory.
        directory_error = 'Workflow directory does not exist.'
        with self.assertRaisesMessage(WorkflowError, directory_error):
            parse_workflow_directory(NONEXISTENT_DIR)

        # Shouldn't be able to parse a directory with no workflow.json.
        with self.assertRaisesMessage(
                WorkflowError,
                'No "workflow.json" manifest file found'):
            parse_workflow_directory(INVALID_WORKFLOW_DIR)

        # Shouldn't be able to parse a directory with no valid versions.
        with self.assertRaisesMessage(
                WorkflowError,
                'Workflow directory {} does not contain any versions'.format(
                    EMPTY_WORKFLOW_DIR)):
            parse_workflow_directory(EMPTY_WORKFLOW_DIR)

        # Should be able to parse a valid directory with two versions.
        parsed = parse_workflow_directory(VALID_WORKFLOW_DIR)
        workflow_json_path = os.path.join(VALID_WORKFLOW_DIR, 'workflow.json')
        with open(workflow_json_path, 'r') as workflow_json_file:
            workflow_data = json.load(workflow_json_file)
        self.assertEqual(workflow_data, parsed['workflow'])

        v1_json_path = os.path.join(VALID_WORKFLOW_DIR, 'v1/version.json')
        with open(v1_json_path, 'r') as v1_json_file:
            v1_data = json.load(v1_json_file)
        self.assertIn(v1_data, parsed['versions'])

        v2_json_path = os.path.join(VALID_WORKFLOW_DIR, 'v2/version.json')
        with open(v2_json_path, 'r') as v2_json_file:
            v2_data = json.load(v2_json_file)
        self.assertIn(v2_data, parsed['versions'])
