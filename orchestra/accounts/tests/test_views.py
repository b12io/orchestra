from django.core.urlresolvers import reverse
from unittest.mock import patch

from orchestra.tests.helpers import OrchestraAuthenticatedTestCase
from orchestra.models import CommunicationPreference
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.tests.helpers.fixtures import setup_models


class AccountSettingsTest(OrchestraAuthenticatedTestCase):

    def setUp(self):
        super().setUp()
        self.user = self.authenticate_user()
        self.url = reverse('orchestra:account_settings')
        self.worker = WorkerFactory(user=self.user)

    def _get_account_settings_mock_data(self):
        return {
            'first_name': 'Mock first',
            'last_name': 'Mock last',
            'slack_username': 'Mock slack',
            'phone_0': '+1',
            'phone_1': '3477761527',
        }

    def test_get_form(self):
        response = self.request_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'accounts/settings.html')

    @patch('orchestra.accounts.forms.get_slack_user_id')
    def test_change_all_fields(self, mock_get_slack_user_id):
        mock_get_slack_user_id.return_value = 'test_id'

        data = self._get_account_settings_mock_data()
        response = self.request_client.post(self.url, data)
        self.assertTrue(response.context['success'])

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, data['first_name'])
        self.assertEqual(self.user.last_name, data['last_name'])

        self.worker.refresh_from_db()
        self.assertEqual(self.worker.slack_username, data['slack_username'])
        self.assertEqual(self.worker.phone, data['phone_0'] + data['phone_1'])
        self.assertEqual(self.worker.slack_user_id, 'test_id')

    @patch('orchestra.accounts.forms.get_slack_user_id')
    def test_missing_fields(self, mock_get_slack_user_id):
        mock_get_slack_user_id.return_value = 'test_id'

        required_fields = self._get_account_settings_mock_data().keys()
        for field in required_fields:
            data = self._get_account_settings_mock_data()
            data.pop(field)
            response = self.request_client.post(self.url, data)
            self.assertFalse(response.context['success'])


class CommunicationPreferenceSettingsTest(OrchestraAuthenticatedTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.url = reverse('orchestra:communication_preference_settings')
        self.user = self.authenticate_user()

        worker = self.workers[0]
        worker.user = self.user
        worker.save()
        # Update this to handle multiple prefs when we have them
        self.comm_pref = CommunicationPreference.objects.filter(
            worker=worker).first()

    def test_get_form(self):
        response = self.request_client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response, 'accounts/communication_preferences_settings.html')

    def _get_mock_data(self):
        return {
            'form-TOTAL_FORMS': 1,
            'form-INITIAL_FORMS': 1,
            'form-MIN_NUM_FORMS': 0,
            'form-MAX_NUM_FORMS': 1,
            'form-0-id': self.comm_pref.id,
        }

    def test_disable_email(self):

        # email is unset and therefore false
        data = self._get_mock_data()

        response = self.request_client.post(self.url, data)
        self.assertTrue(response.context['success'])

        self.comm_pref.refresh_from_db()
        self.assertFalse(self.comm_pref.methods.email.is_set)
