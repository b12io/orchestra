from unittest.mock import patch

from django.db.models import Q
from django.test import override_settings

from orchestra.communication.slack import create_project_slack_group
from orchestra.google_apps.convenience import Service
from orchestra.google_apps.convenience import create_project_google_folder
from orchestra.models import Project
from orchestra.models import Task
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.google_apps import mock_create_drive_service
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import complete_and_skip_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks


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

    @override_settings(ORCHESTRA_SLACK_EXPERTS_ENABLED=True)
    @patch('orchestra.communication.tests.helpers.slack.Groups.archive')
    def test_complete_all_tasks_slack_annoucement(self, mock_slack_archive):
        project = self.projects['single_human_step']
        create_subsequent_tasks(project)
        task = Task.objects.get(project=project)
        assign_task(self.workers[1].id, task.id)
        self.assertEqual(project.status, Project.Status.ACTIVE)
        self.assertFalse(mock_slack_archive.called)

        complete_and_skip_task(task.id)
        create_subsequent_tasks(project)
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.COMPLETED)
        self.assertTrue(mock_slack_archive.called)

    @override_settings(ORCHESTRA_SLACK_EXPERTS_ENABLED=True)
    @patch('orchestra.communication.tests.helpers.slack.Groups.archive')
    def test_completion_ends_project_true(self, mock_slack_archive):
        project = self.projects['test_human_and_machine']
        create_subsequent_tasks(project)

        task = project.tasks.first()
        assign_task(self.workers[1].id, task.id)
        self.assertEqual(project.status, Project.Status.ACTIVE)
        self.assertFalse(mock_slack_archive.called)
        task.step.completion_ends_project = True
        task.step.save()
        task.status = Task.Status.COMPLETE
        task.save()

        create_subsequent_tasks(project)
        project.refresh_from_db()
        incomplete_tasks = (Task.objects.filter(project=project).exclude(
            Q(status=Task.Status.COMPLETE) |
            Q(status=Task.Status.ABORTED))).count()
        self.assertTrue(incomplete_tasks > 0)
        self.assertEqual(project.status, Project.Status.COMPLETED)
        self.assertTrue(mock_slack_archive.called)

    @override_settings(ORCHESTRA_SLACK_EXPERTS_ENABLED=True)
    @patch('orchestra.communication.tests.helpers.slack.Groups.archive')
    def test_completion_ends_project_false(self, mock_slack_archive):
        project = self.projects['test_human_and_machine']
        create_subsequent_tasks(project)

        task = project.tasks.first()
        assign_task(self.workers[1].id, task.id)
        self.assertEqual(project.status, Project.Status.ACTIVE)
        self.assertFalse(mock_slack_archive.called)
        task.status = Task.Status.COMPLETE
        task.save()

        create_subsequent_tasks(project)
        project.refresh_from_db()
        incomplete_tasks = (Task.objects.filter(project=project).exclude(
            Q(status=Task.Status.COMPLETE) |
            Q(status=Task.Status.ABORTED))).count()
        self.assertTrue(incomplete_tasks > 0)
        self.assertEqual(project.status, Project.Status.ACTIVE)
        self.assertFalse(mock_slack_archive.called)
