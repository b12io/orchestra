from django.core.urlresolvers import reverse

from orchestra.tests.helpers import OrchestraAuthenticatedTestCase
from orchestra.models import CommunicationPreference
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.tests.helpers.fixtures import setup_models


class AccountSettingsTest(OrchestraAuthenticatedTestCase):

    def setUp(self):
        super().setUp()
        self.request_client, self.user = self.authenticate_user()
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

    def test_change_all_fields(self):
        data = self._get_account_settings_mock_data()
        response = self.request_client.post(self.url, data)
        self.assertTrue(response.context['success'])

        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, data['first_name'])
        self.assertEqual(self.user.last_name, data['last_name'])

        self.worker.refresh_from_db()
        self.assertEqual(self.worker.slack_username, data['slack_username'])
        self.assertEqual(self.worker.phone, data['phone_0'] + data['phone_1'])

    def test_missing_fields(self):
        required_fields = self._get_account_settings_mock_data().keys()
        for field in required_fields:
            data = self._get_account_settings_mock_data()
            data.pop(field)
            response = self.request_client.post(self.url, data)
            self.assertFalse(response.context['success'])


class CommunicationPreferenceSettingsTest(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.url = reverse('orchestra:communication_preference_settings')
        self.request_client = RequestClient()

        worker = self.workers[0]
        # Update this to handle multiple prefs when we have them
        self.comm_pref = CommunicationPreference.objects.filter(
            worker=worker).first()
        self.user = worker.user
        self.password = 'test'
        self.user.set_password(self.password)
        self.user.is_active = True
        self.user.save()
        self.login()

    def login(self):
        self.assertTrue(self.request_client.login(
            username=self.user.username, password=self.password))

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
            'form-0-id': 1,
        }

    def test_disable_email(self):

        data = self._get_mock_data()
        # email is unset and therefore false
        data['form-0-methods'] = 'slack'

        response = self.request_client.post(self.url, data)
        self.assertTrue(response.context['success'])

        self.comm_pref.refresh_from_db()
        self.assertEqual(self.comm_pref.methods.slack,
                         CommunicationPreference.methods.slack)
        self.assertEqual(self.comm_pref.methods.email,
                         ~CommunicationPreference.methods.email)

    def test_disable_slack(self):

        data = self._get_mock_data()
        # slack is unset and therefore false
        data['form-0-methods'] = 'email'

        response = self.request_client.post(self.url, data)
        self.assertTrue(response.context['success'])

        self.comm_pref.refresh_from_db()
        self.assertEqual(self.comm_pref.methods.slack,
                         ~CommunicationPreference.methods.slack)
        self.assertEqual(self.comm_pref.methods.email,
                         CommunicationPreference.methods.email)

    def test_disable_all(self):

        data = self._get_mock_data()

        response = self.request_client.post(self.url, data)
        self.assertTrue(response.context['success'])

        self.comm_pref.refresh_from_db()
        self.assertEqual(self.comm_pref.methods.slack,
                         ~CommunicationPreference.methods.slack)
        self.assertEqual(self.comm_pref.methods.email,
                         ~CommunicationPreference.methods.email)
