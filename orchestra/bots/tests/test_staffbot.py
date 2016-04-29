from django.test import override_settings

from orchestra.tests.helpers import OrchestraTestCase
from orchestra.bots.errors import SlackCommandInvalidRequest
from orchestra.bots.staffbot import StaffBot
from orchestra.bots.tests.fixtures import get_mock_slack_data


class BotTest(OrchestraTestCase):

    def test_request_validation(self):
        """
            Ensure we only listen to valid requests.
        """
        mock_slack_data = get_mock_slack_data()
        # Test all requests allowed
        bot = StaffBot()
        self.assertEqual(mock_slack_data, bot.validate(mock_slack_data))

        # verify we validate the token
        with override_settings(SLACK_STAFFBOT_TOKEN=''):
            bot = StaffBot()
            with self.assertRaises(SlackCommandInvalidRequest):
                bot.validate(mock_slack_data)

        # verify that we perform validation on each of the fields
        validated_fields = ['allowed_team_ids', 'allowed_domains',
                            'allowed_channel_ids', 'allowed_channel_names',
                            'allowed_user_ids', 'allowed_user_names',
                            'allowed_commands']
        for field in validated_fields:
            config = {field: ''}
            bot = StaffBot(**config)
            with self.assertRaises(SlackCommandInvalidRequest):
                bot.validate(mock_slack_data)
