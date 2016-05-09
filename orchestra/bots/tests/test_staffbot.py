from unittest.mock import patch

from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.bots.errors import SlackUserUnauthorized
from orchestra.bots.staffbot import StaffBot
from orchestra.bots.tests.fixtures import get_mock_slack_data
from orchestra.models import CommunicationPreference
from orchestra.models import StaffingRequestInquiry
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import is_worker_certified_for_task


class StaffBotTest(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = self.workers[0]
        self.worker.user.is_superuser = True
        self.worker.user.save()
        patcher = patch(
            ('orchestra.bots.staffbot.StaffBot'
             '._send_staffing_request_by_slack'))
        patcher.start()
        self.addCleanup(patcher.stop)

    def _get_worker_for_task(self, task, role):
        # Get certified reviewer
        for worker in Worker.objects.all():
            if is_worker_certified_for_task(worker, task, role):
                return worker

    def _test_staffing_requests(self, worker, task, command,
                                can_slack=False, can_mail=False):
        bot = StaffBot()
        communication_type = (CommunicationPreference.CommunicationType
                              .NEW_TASK_AVAILABLE.value)
        communication_preference = CommunicationPreference.objects.get(
            worker=worker,
            communication_type=communication_type)
        communication_preference.methods.slack = can_slack
        communication_preference.methods.email = can_mail
        communication_preference.save()

        data = get_mock_slack_data(
            text=command,
            user_id=self.worker.slack_user_id)
        bot.dispatch(data)
        self.assertEquals(StaffingRequestInquiry.objects.filter(
            communication_preference__worker_id=worker,
            task=task).count(), can_slack + can_mail)

    def test_assert_validate_error(self):
        bot = StaffBot()
        with self.assertRaises(SlackUserUnauthorized):
            mock_slack_data = get_mock_slack_data(text='staff 5')
            bot.dispatch(mock_slack_data)

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
        mock_slack_data = get_mock_slack_data(
            text='staff 5',
            user_id=self.worker.slack_user_id)

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

    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_mail')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_staff_command(self, mock_slack, mock_mail):
        """
        Test that the staffing logic is properly executed for the
        staff command.
        """
        task = (Task.objects
                .filter(status=Task.Status.AWAITING_PROCESSING)
                .first())

        # Get certified worker
        worker = self._get_worker_for_task(
            task, WorkerCertification.Role.ENTRY_LEVEL)

        self._test_staffing_requests(worker, task, 'staff {}'.format(task.id),
                                     can_slack=False, can_mail=False)
        self._test_staffing_requests(worker, task, 'staff {}'.format(task.id),
                                     can_slack=True, can_mail=True)

        # Change the task state to pending review
        task = assign_task(worker.id, task.id)
        task.status = Task.Status.PENDING_REVIEW
        task.save()

        StaffingRequestInquiry.objects.all().delete()

        worker = self._get_worker_for_task(task,
                                           WorkerCertification.Role.REVIEWER)
        self._test_staffing_requests(worker, task, 'staff {}'.format(task.id),
                                     can_slack=False, can_mail=False)
        self._test_staffing_requests(worker, task, 'staff {}'.format(task.id),
                                     can_slack=True, can_mail=True)
        self.assertTrue(mock_mail.called)
        self.assertTrue(mock_slack.called)

    def test_staff_command_errors(self):
        """
        Test that the staffing logic errors are raised during
        staff command.
        """
        bot = StaffBot()
        data = get_mock_slack_data(
            text='staff 999999999999',
            user_id=self.worker.slack_user_id)

        response = bot.dispatch(data)
        self.assertEqual(response.get('text'),
                         bot.task_does_not_exist_error.format('999999999999'))

        data['text'] = 'staff'
        response = bot.dispatch(data)
        self.assertTrue(bot.default_error_text in response.get('text'))

        task = TaskFactory(status=Task.Status.COMPLETE)
        data['text'] = 'staff {}'.format(task.id)
        response = bot.dispatch(data)
        self.assertEquals(response.get('text'),
                          bot.task_assignment_error
                          .format(task.id,
                                  'Status incompatible with new assignment'))

    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_mail')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_restaff_command(self, mock_slack, mock_mail):
        """
        Test that the restaffing logic is properly executed for the
        restaff command.
        """
        task = (Task.objects
                .filter(status=Task.Status.AWAITING_PROCESSING)
                .first())

        # Get certified worker
        worker = self._get_worker_for_task(
            task, WorkerCertification.Role.ENTRY_LEVEL)
        task = assign_task(worker.id, task.id)
        command = 'restaff {} {}'.format(task.id, worker.user.username)

        self._test_staffing_requests(worker, task, command,
                                     can_slack=False, can_mail=False)

        task.status = Task.Status.AWAITING_PROCESSING
        task.save()
        TaskAssignment.objects.filter(worker=worker,
                                      task=task).delete()
        task = assign_task(worker.id, task.id)
        self._test_staffing_requests(worker, task, command,
                                     can_slack=True, can_mail=True)
        self.assertTrue(mock_mail.called)
        self.assertTrue(mock_slack.called)

    def test_restaff_command_errors(self):
        """
        Test that the staffing logic errors are raised during
        staff command.
        """
        bot = StaffBot()
        data = get_mock_slack_data(
            text='restaff 999999999999 unknown',
            user_id=self.worker.slack_user_id)

        response = bot.dispatch(data)
        self.assertEqual(response.get('text'),
                         bot.worker_does_not_exist.format('unknown'))

        worker = WorkerFactory(user__username='slackusername')
        data['text'] = 'restaff 999999999999 slackusername'
        response = bot.dispatch(data)
        self.assertEqual(response.get('text'),
                         bot.task_does_not_exist_error.format('999999999999'))

        data['text'] = 'restaff'
        response = bot.dispatch(data)
        self.assertTrue(bot.default_error_text in response.get('text'))

        task = TaskFactory(status=Task.Status.COMPLETE)
        command = 'restaff {} {}'.format(task.id, worker.user.username)

        data['text'] = command
        response = bot.dispatch(data)
        self.assertEquals(response.get('text'),
                          (bot.task_assignment_does_not_exist_error
                           .format(worker.user.username, task.id)))
