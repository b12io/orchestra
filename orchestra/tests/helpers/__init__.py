import json
from unittest.mock import patch

from django.test import TestCase
from django.test import override_settings

from orchestra.tests.helpers.notifications import MockMail
from orchestra.tests.helpers.slack import MockSlacker


@override_settings(
    ORCHESTRA_PATHS=(('orchestra.tests.helpers.workflow', 'workflow'),
                     ('orchestra.tests.helpers.workflow', 'workflow2'),
                     ('orchestra.tests.helpers.workflow',
                      'assignment_policy_workflow')))
class OrchestraTestCase(TestCase):

    def setUp(self):  # noqa
        super(OrchestraTestCase, self).setUp()
        # maxDiff prevents the test runner from suppressing the diffs on
        # assertEquals, which is nice when you have large string comparisons as
        # we do in this test to assert the expected JSON blob responses.
        self.maxDiff = None

        # Without patching the slack API calls, the tests hang indefinitely
        # and you'll need to restart your boot2docker.
        self.slack = MockSlacker()
        patcher = patch('orchestra.slack.slacker.Slacker',
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
