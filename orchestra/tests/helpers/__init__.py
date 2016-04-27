import json
from unittest.mock import patch

from django.test import TestCase
from django.test import TransactionTestCase

from orchestra.tests.helpers.notifications import MockMail
from orchestra.tests.helpers.slack import MockSlacker


class OrchestraTestHelpersMixin(object):

    def setUp(self):  # noqa
        super().setUp()
        # maxDiff prevents the test runner from suppressing the diffs on
        # assertEquals, which is nice when you have large string comparisons as
        # we do in this test to assert the expected JSON blob responses.
        self.maxDiff = None

        # Without patching the slack API calls, the tests hang indefinitely
        # and you'll need to restart your boot2docker.
        self.slack = MockSlacker()
        patcher = patch('orchestra.communication.slack.slacker.Slacker',
                        return_value=self.slack)
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
        self.assertEquals(response.status_code, expected_status_code)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned,
                          expected_json_payload)

    def _submit_assignment(self, client, task_id, data=None,
                           seconds=1, command='submit'):
        if data is None:
            data = {'test': 'test'}
        request = json.dumps(
            {'task_id': task_id, 'task_data': data, 'command_type': command})

        return client.post(
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


class OrchestraTestCase(OrchestraTestHelpersMixin, TestCase):
    # NOTE(lydia): Mixin should go before TestCase because when mixin calls
    # super().setUp(), it looks to the base of mixin (which is Object - doesn't
    # have setUp() defined, then to the right for setUp() (which is defined
    # in TestCase)
    pass


class OrchestraTransactionTestCase(OrchestraTestHelpersMixin,
                                   TransactionTestCase):
    # NOTE(lydia): See note above about multiple inheritance ordering.
    pass
