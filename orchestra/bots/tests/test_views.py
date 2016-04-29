from django.core.urlresolvers import reverse
from django.test import override_settings
from django.test import Client as RequestClient

from orchestra.bots.staffbot import BaseBot
from orchestra.bots.tests.fixtures import get_mock_slack_data
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.utils.load_json import load_encoded_json


class StaffBotViewTest(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        self.request_client = RequestClient()
        self.url = reverse('orchestra:staffbot')

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

    def test_staff_command(self):
        data = get_mock_slack_data()
        data['text'] = 'staff 5'
        response = self.request_client.post(self.url, data)
        self.assert_response(response)

        data['text'] = 'staff'
        response = self.request_client.post(self.url, data)
        self.assert_response(
            response, default_error_text=BaseBot.default_error_text)

    def test_restaff_command(self):
        data = get_mock_slack_data()
        data['text'] = 'restaff 5 username'
        response = self.request_client.post(self.url, data)
        self.assert_response(response)

        data['text'] = 'restaff 5'
        response = self.request_client.post(self.url, data)
        self.assert_response(
            response, default_error_text=BaseBot.default_error_text)
