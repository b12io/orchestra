from django.core.urlresolvers import reverse
from django.test import override_settings
from django.test import Client as RequestClient
from unittest.mock import patch

from orchestra.bots.tests.fixtures import get_mock_slack_data
from orchestra.models import Task
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.load_json import load_encoded_json


class StaffBotViewTest(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.request_client = RequestClient()
        self.url = reverse('orchestra:bots:staffbot')

    def assert_response(self, response, error=False, default_error_text=None):
        self.assertEqual(response.status_code, 200)
        data = load_encoded_json(response.content)
        self.assertEqual('error' in data, error)
        if default_error_text is not None:
            self.assertTrue(default_error_text in data.get('text', ''))

    def test_get_not_allowed(self):
        response = self.request_client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_post_valid_data(self):
        data = get_mock_slack_data()
        response = self.request_client.post(self.url, data)
        self.assert_response(response)

    @override_settings(SLACK_STAFFBOT_TOKEN='')
    def test_post_invalid_data(self):
        data = get_mock_slack_data()
        response = self.request_client.post(self.url, data)
        self.assert_response(response, error=True)

    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_mail')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_staff_command(self, mock_slack, mock_mail):
        task = TaskFactory(status=Task.Status.AWAITING_PROCESSING)
        data = get_mock_slack_data(text='staff {}'.format(task.id))
        response = self.request_client.post(self.url, data)
        self.assertEqual(load_encoded_json(response.content).get('text'),
                         'Staffed task {}!'.format(task.id))

        task = TaskFactory(status=Task.Status.PENDING_REVIEW)
        data = get_mock_slack_data(text='staff {}'.format(task.id))
        response = self.request_client.post(self.url, data)
        self.assertEqual(load_encoded_json(response.content).get('text'),
                         'Staffed task {}!'.format(task.id))

    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_mail')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_restaff_command(self, mock_slack, mock_mail):
        data = get_mock_slack_data()
        task = (
            Task.objects.filter(status=Task.Status.AWAITING_PROCESSING)
            .first())
        worker = self.workers[0]
        task = assign_task(worker.id, task.id)
        command = 'restaff {} {}'.format(task.id, worker.user.username)

        data = get_mock_slack_data(text=command)
        response = self.request_client.post(self.url, data)
        self.assertEqual(load_encoded_json(response.content).get('text'),
                         'Restaffed task {}!'.format(task.id))
