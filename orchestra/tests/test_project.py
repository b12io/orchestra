from unittest.mock import patch

from django.test import override_settings

from orchestra.communication.slack import create_project_slack_group
from orchestra.google_apps.convenience import Service
from orchestra.google_apps.convenience import create_project_google_folder
from orchestra.models import Project
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.google_apps import mock_create_drive_service


class BasicTaskLifeCycleTestCase(OrchestraTestCase):
    """
    Test project module helper functions.
    """
    def setUp(self):
        super().setUp()
        setup_models(self)

    @override_settings(GOOGLE_APPS=True)
    @patch.object(Service, '_create_drive_service',
                  new=mock_create_drive_service)
    def test_create_project_google_folder(self):
        project = self.projects['empty_project']
        # TODO(jrbotros): add additional functionality to google mock
        project_folder = create_project_google_folder(project)
        self.assertEqual(project_folder['id'], 1)
        self.assertEqual(
            project.team_messages_url, 'http://a.google.com/link')

    @override_settings(ORCHESTRA_SLACK_EXPERTS_ENABLED=True)
    def test_create_project_slack_group(self):
        groups = self.slack.data['groups']
        num_groups = len(groups)
        project = ProjectFactory(
            workflow_version=self.workflow_versions['test_workflow'])
        self.assertFalse(project.id in groups)
        group_id = create_project_slack_group(project)
        self.assertEqual(len(groups), num_groups + 1)
        self.assertTrue(group_id in groups)
        project = Project.objects.get(id=project.id)
        self.assertEqual(group_id, project.slack_group_id)
