from django.core.urlresolvers import reverse
from django.test import override_settings
from django.test import Client as RequestClient

from orchestra.bots.tests.fixtures import get_mock_slack_data
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.utils.load_json import load_encoded_json


class StaffBotViewTest(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        self.request_client = RequestClient()
        self.url = reverse('orchestra:staffbot')

    def test_get_not_allowed(self):
        response = self.request_client.get(self.url)
        self.assertEqual(response.status_code, 405)

    def test_post_valid_data(self):
        data = get_mock_slack_data()
        response = self.request_client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        load_encoded_json(response.content)

    @override_settings(SLACK_STAFFBOT_TOKEN='')
    def test_invalid_request(self):
        data = get_mock_slack_data()
        response = self.request_client.post(self.url, data)
        self.assertEqual(response.status_code, 200)
        data = load_encoded_json(response.content)
        self.assertTrue('error' in data)
