from django.core.urlresolvers import reverse
from django.test import Client as RequestClient

from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import UserFactory


class AccountSettingsTest(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        self.url = reverse('orchestra:account_settings')
        self.request_client = RequestClient()

        self.password = 'test'
        self.user = UserFactory(
            username='test_account_settings',
            email='test_account_settings@orchestra.com',
            first_name='first name',
            last_name='last name',
            password=self.password)
        self.user.is_active = True
        self.user.save()
        self.login()

    def _get_account_settings_mock_data(self):
        return {
            'first_name': 'Mock first',
            'last_name': 'Mock last',
        }

    def _get_account_settings_current_data(self):
        return {
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        }

    def login(self):
        self.assertTrue(self.request_client.login(
            username=self.user.username, password=self.password))

    def test_get_form(self):
        response = self.request_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/settings.html')

    def test_change_all_fields(self):
        data = self._get_account_settings_mock_data()
        response = self.request_client.post(self.url, data)
        self.assertTrue(response.context['success'])
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, data['first_name'])
        self.assertEqual(self.user.last_name, data['last_name'])

    def test_missing_fields(self):
        required_fields = self._get_account_settings_mock_data().keys()
        for field in required_fields:
            data = self._get_account_settings_mock_data()
            data.pop(field)
            response = self.request_client.post(self.url, data)
            self.assertFalse(response.context['success'])
