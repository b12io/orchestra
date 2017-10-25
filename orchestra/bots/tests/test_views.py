from unittest.mock import patch

from django.core.urlresolvers import reverse
from django.test import Client as RequestClient
from django.test import override_settings

from orchestra.bots.staffbot import StaffBot
from orchestra.bots.tests.fixtures import get_mock_slack_data
from orchestra.models import Task
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.load_json import load_encoded_json
from orchestra.utils.task_lifecycle import assign_task


class StaffBotViewTest(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = self.workers[0]
        self.worker.user.is_superuser = True
        self.worker.user.save()

        self.request_client = RequestClient(username=self.worker.user.username,
                                            password='defaultpassword')
        self.url = reverse('orchestra:bots:staffbot')
        self.staffbot = StaffBot()

    def assert_response(self, response, default_error_text=None):
        self.assertEqual(response.status_code, 200)
        data = load_encoded_json(response.content)
        if default_error_text is not None:
            self.assertTrue(default_error_text in data.get('text', ''))

    def test_unauthorized_user(self):
        worker1 = self.workers[1]
        request_client = RequestClient(username=worker1.user.username,
                                       password='defaultpassword')
        data = get_mock_slack_data(
            user_id=worker1.slack_user_id)
        response = request_client.post(self.url, data)
        self.assert_response(response,
                             default_error_text=StaffBot.not_authorized_error)

        data['user_id'] = 'fake_id'
        response = request_client.post(self.url, data)
        self.assert_response(response,
                             default_error_text='not found')

    def test_get_not_allowed(self):
        response = self.request_client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_post_valid_data(self):
        data = get_mock_slack_data(
            user_id=self.worker.slack_user_id)
        response = self.request_client.post(self.url, data)
        self.assert_response(response)

    @override_settings(ORCHESTRA_SLACK_STAFFBOT_TOKEN='')
    def test_post_invalid_token(self):
        data = get_mock_slack_data(
            user_id=self.worker.slack_user_id)
        response = self.request_client.post(self.url, data)
        self.assert_response(
            response, default_error_text='Invalid token')

    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_mail')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_staff_command(self, mock_slack, mock_mail):
        task = TaskFactory(status=Task.Status.AWAITING_PROCESSING)
        data = get_mock_slack_data(
            text='staff {}'.format(task.id),
            user_id=self.worker.slack_user_id)
        response = self.request_client.post(self.url, data)
        self.assertEqual(
            load_encoded_json(response.content)['attachments'][0]['text'],
            self.staffbot.staffing_success.format(task.id))

        task = TaskFactory(status=Task.Status.PENDING_REVIEW)
        data = get_mock_slack_data(
            text='staff {}'.format(task.id),
            user_id=self.worker.slack_user_id)

        response = self.request_client.post(self.url, data)
        self.assertEqual(
            load_encoded_json(response.content)['attachments'][0]['text'],
            self.staffbot.staffing_success.format(task.id))

    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_mail')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_restaff_command(self, mock_slack, mock_mail):
        data = get_mock_slack_data(user_id=self.worker.slack_user_id)

        task = (
            Task.objects.filter(status=Task.Status.AWAITING_PROCESSING)
            .first())
        worker = self.workers[0]
        task = assign_task(worker.id, task.id)
        command = 'restaff {} {}'.format(task.id, worker.user.username)
        data = get_mock_slack_data(
            text=command,
            user_id=self.worker.slack_user_id)

        response = self.request_client.post(self.url, data)
        self.assertEqual(
            load_encoded_json(response.content)['attachments'][0]['text'],
            self.staffbot.restaffing_success.format(task.id))
