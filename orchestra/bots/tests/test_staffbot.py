from orchestra.tests.helpers import OrchestraTestCase
from orchestra.bots.staffbot import StaffBot
from orchestra.bots.tests.fixtures import get_mock_slack_data


class StaffBotTest(OrchestraTestCase):

    def test_commands(self):
        """
        Ensure that the bot can handle the following commands:
        /staffbot staff <task_id>
        /staffbot restaff <task_id> <username>

        This test only validates that the commands are processed, other
        tests verify the functionality of the command execution.
        """
        bot = StaffBot()

        # Test staff command
        mock_slack_data = get_mock_slack_data()
        mock_slack_data['text'] = 'staff 5'
        response = bot.dispatch(mock_slack_data)
        self.assertFalse(bot.default_error_text in response.get('text', ''))

        # Test the restaff command
        mock_slack_data['text'] = 'restaff 5 username'
        response = bot.dispatch(mock_slack_data)
        self.assertFalse(bot.default_error_text in response.get('text', ''))

        # Test we fail gracefully
        mock_slack_data['text'] = 'invalid command'
        response = bot.dispatch(mock_slack_data)
        self.assertTrue(bot.default_error_text in response.get('text', ''))

    def test_staff_command(self):
        """
        Test that the staffing logic is properly executed for the
        staff command.
        """
        bot = StaffBot()

        # Test staff command
        mock_slack_data = get_mock_slack_data()
        mock_slack_data['text'] = 'staff 5'
        response = bot.dispatch(mock_slack_data)
        self.assertEqual(response.get('text'), 'Staffed task 5!')

        mock_slack_data['text'] = 'staff'
        response = bot.dispatch(mock_slack_data)
        self.assertTrue(bot.default_error_text in response.get('text'))

    def test_restaff_command(self):
        """
        Test that the restaffing logic is properly executed for the
        restaff command.
        """
        bot = StaffBot()

        # Test staff command
        mock_slack_data = get_mock_slack_data()
        mock_slack_data['text'] = 'restaff 5 username'
        response = bot.dispatch(mock_slack_data)
        self.assertEqual(
            response.get('text'), 'Restaffed task 5 for username!'
        )

        mock_slack_data['text'] = 'restaff 5'
        response = bot.dispatch(mock_slack_data)
        self.assertTrue(bot.default_error_text in response.get('text'))
