from orchestra.bots.basebot import BaseBot
from orchestra.bots.errors import SlackCommandInvalidRequest
from orchestra.bots.tests.fixtures import get_mock_slack_data
from orchestra.tests.helpers import OrchestraTestCase


class BaseBotTest(OrchestraTestCase):
    token = get_mock_slack_data().get('token')

    def test_help(self):
        bot = BaseBot(self.token)
        mock_slack_data = get_mock_slack_data(text='help')
        with self.assertRaises(NotImplementedError):
            bot.dispatch(mock_slack_data)

    def test_validate(self):
        """
            Ensure we only listen to valid requests.
        """
        mock_slack_data = get_mock_slack_data()
        # Test all requests allowed
        bot = BaseBot(self.token)
        self.assertEqual(mock_slack_data, bot.validate(mock_slack_data))

        # verify we validate the token
        bot = BaseBot('')
        with self.assertRaises(SlackCommandInvalidRequest):
            bot.validate(mock_slack_data)

        # verify that we perform validation on each of the fields
        validated_fields = ['allowed_team_ids', 'allowed_domains',
                            'allowed_channel_ids', 'allowed_channel_names',
                            'allowed_user_ids', 'allowed_user_names',
                            'allowed_commands']
        for field in validated_fields:
            config = {field: []}
            bot = BaseBot(self.token, **config)
            with self.assertRaises(SlackCommandInvalidRequest):
                bot.validate(mock_slack_data)
        config = {'allowed_{}s'.format(field): [mock_slack_data.get(field)]
                  for field in validated_fields}
        bot = BaseBot(self.token, **config)
        self.assertEqual(mock_slack_data, bot.validate(mock_slack_data))

    def test_dispatch(self):
        bot = BaseBot(self.token)
        bot.commands = (
            (r'test_command (?P<test_param>[0-9]+)', 'test_command'),
        )

        def test_command(test_param):
            return test_param
        bot.test_command = test_command

        # Assign the testing command
        bot.__init__(self.token)

        # Test a valid command
        text = 'test_command 5'
        mock_slack_data = get_mock_slack_data(text=text)
        result = bot.dispatch(mock_slack_data)
        self.assertEqual('5', result)

        # Test a valid command with missing param
        text = 'test_command'
        mock_slack_data = get_mock_slack_data(text=text)
        result = bot.dispatch(mock_slack_data)
        self.assertEqual(bot.no_command_found(text), result)

        # Test invalid command
        text = 'invalid'
        mock_slack_data = get_mock_slack_data(text=text)
        result = bot.dispatch(mock_slack_data)
        self.assertEqual(bot.no_command_found(text), result)
