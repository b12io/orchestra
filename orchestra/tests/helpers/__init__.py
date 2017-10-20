import json
from unittest.mock import patch

from django.test import override_settings
from django.test import TestCase
from django.test import TransactionTestCase

from orchestra.tests.helpers.notifications import MockMail
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.communication.tests.helpers.slack import MockSlacker
from orchestra.utils.load_json import load_encoded_json

# Don't log logger errors.
import logging
logging.disable(logging.CRITICAL)


class OrchestraTestHelpersMixin(object):

    def setUp(self):
        super().setUp()
        # Rename the django Client to request_client
        self.request_client = self.client
        # maxDiff prevents the test runner from suppressing the diffs on
        # assertEqual, which is nice when you have large string comparisons as
        # we do in this test to assert the expected JSON blob responses.
        self.maxDiff = None

        # Without patching the slack API calls, the tests hang indefinitely
        # and you'll need to restart your boot2docker.
        self.slack = MockSlacker()
        patcher = patch(
            'orchestra.communication.slack.Slacker',
            return_value=self.slack
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.slack.clear)

        # Though mail isn't sent in django tests, we mock out send_mail here to
        # have access to sent messages for testing.
        self.mail = MockMail()
        patcher = patch('orchestra.utils.notifications.send_mail',
                        side_effect=self.mail.send_mail)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.mail.clear)

    def ensure_response(self,
                        response,
                        expected_json_payload,
                        expected_status_code):
        self.assertEqual(response.status_code, expected_status_code)
        returned = load_encoded_json(response.content)
        self.assertEqual(returned,
                         expected_json_payload)

    def _submit_assignment(self, request_client, task_id, data=None,
                           seconds=1, command='submit'):
        if data is None:
            data = {'test': 'test'}
        request = json.dumps(
            {'task_id': task_id, 'task_data': data, 'command_type': command})

        return request_client.post(
            '/orchestra/api/interface/submit_task_assignment/',
            request,
            content_type='application/json')

    def assertModelInstanceExists(self,
                                  model_class,
                                  lookup_attributes,
                                  check_attributes={}):
        try:
            model_instance = model_class.objects.get(**lookup_attributes)
        except model_class.DoesNotExist:
            self.fail('{} instance not created in database.'
                      .format(str(model_class)))
        for attribute_name, expected_value in check_attributes.items():
            self.assertEqual(getattr(model_instance, attribute_name),
                             expected_value)
        return model_instance

    def assertModelInstanceNotExists(self, model_class, lookup_attributes):
        with self.assertRaises(model_class.DoesNotExist):
            model_class.objects.get(**lookup_attributes)


class AuthenticatedUserMixin(object):

    def authenticate_user(self):
        password = 'test'
        auth_user = UserFactory(
            username='test_user',
            email='test_user@orchestra.com',
            first_name='first name',
            last_name='last name',
            is_active=True,
            password=password)
        self.assertTrue(self.request_client.login(
            username=auth_user.username, password=password))
        return auth_user


@override_settings(ORCHESTRA_SLACK_STAFFBOT_TOKEN='test-token')
class OrchestraTestCase(OrchestraTestHelpersMixin, TestCase):
    # NOTE(lydia): Mixin should go before TestCase because when mixin calls
    # super().setUp(), it looks to the base of mixin (which is Object - doesn't
    # have setUp() defined, then to the right for setUp() (which is defined
    # in TestCase)
    pass


@override_settings(ORCHESTRA_SLACK_STAFFBOT_TOKEN='test-token')
class OrchestraTransactionTestCase(OrchestraTestHelpersMixin,
                                   TransactionTestCase):
    # NOTE(lydia): See note above about multiple inheritance ordering.
    pass


class OrchestraAuthenticatedTestCase(OrchestraTestCase,
                                     AuthenticatedUserMixin):
    # NOTE(lydia): See note above about multiple inheritance ordering.
    pass


class OrchestraModelTestCase(OrchestraTestCase):
    """
    This is a basic test to ensure that we update the __str__ method on models
    when we modify fields. It is a simple way to catch errors before we break
    the admin page because of model changes.

    NOTE: This does not test the validity of __str__ it just verifies that the
    function can run without error.
    """
    __test__ = False
    model = None
    model_kwargs = {}

    def test_to_string(self):
        instance = self.model(**self.model_kwargs)
        self.assertEqual(str(instance), str(instance))


class EndpointTestCase(OrchestraTestCase):

    def _verify_bad_request(self, response, message):
        self.assertEqual(response.status_code, 400)
        data = load_encoded_json(response.content)
        self.assertEqual(data['message'], message)
        self.assertEqual(data['error'], 400)
