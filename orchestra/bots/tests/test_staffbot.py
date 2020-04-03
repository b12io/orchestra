from datetime import timedelta
from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

from orchestra.bots.errors import SlackUserUnauthorized
from orchestra.bots.staffbot import StaffBot
from orchestra.bots.tests.fixtures import get_mock_slack_data
from orchestra.communication.mail import html_from_plaintext
from orchestra.communication.staffing import send_staffing_requests
from orchestra.models import CommunicationPreference
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import Task
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import StaffBotRequestFactory
from orchestra.tests.helpers.fixtures import StaffingRequestInquiryFactory
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import is_worker_certified_for_task


def _noop_details(task_details):
    return ''


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
        StaffBotRequest.objects.all().delete()
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
        send_staffing_requests(worker_batch_size=20,
                               frequency=timedelta(minutes=0))
        self.assertEqual(StaffingRequestInquiry.objects.filter(
            communication_preference__worker_id=worker,
            request__task=task).count(), can_slack + can_mail)

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

    @patch('orchestra.bots.staffbot.send_mail')
    @patch('orchestra.bots.staffbot.message_experts_slack_group')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_staff_command(self, mock_slack, mock_experts_slack, mock_mail):
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
                                     can_slack=True, can_mail=True)

        self._test_staffing_requests(worker, task, 'staff {}'.format(task.id),
                                     can_slack=False, can_mail=False)

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
        self.assertTrue(mock_experts_slack.called)
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
        self.assertEqual(response['attachments'][0]['text'],
                         bot.task_does_not_exist_error.format('999999999999'))

        data['text'] = 'staff'
        response = bot.dispatch(data)
        self.assertTrue(bot.default_error_text in response.get('text'))

        task = TaskFactory(status=Task.Status.COMPLETE)
        data['text'] = 'staff {}'.format(task.id)
        response = bot.dispatch(data)
        self.assertEqual(response['attachments'][0]['text'],
                         bot.task_assignment_error
                         .format(task.id,
                                 'Status incompatible with new assignment'))

    @patch('orchestra.bots.staffbot.send_mail')
    @patch('orchestra.bots.staffbot.message_experts_slack_group')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_staff_close_requests(self, mock_slack,
                                  mock_experts_slack, mock_mail):
        """
        Test that existing staffbot requests for a task is closed when
        a staff function is called.
        """
        CLOSED = StaffBotRequest.Status.CLOSED.value

        bot = StaffBot()
        task = TaskFactory()
        init_num_request = StaffBotRequest.objects.filter(task=task).count()
        self.assertEqual(init_num_request, 0)

        bot.staff(task.id)
        requests = StaffBotRequest.objects.filter(task=task)
        num_request = requests.count()
        self.assertEqual(num_request, init_num_request + 1)
        self.assertNotEqual(requests.last().status, CLOSED)

        # Calling staff on the same task should close the previous request
        # and create a new one.
        bot.staff(task.id)
        requests = list(StaffBotRequest.objects.filter(task=task))
        num_request = len(requests)
        self.assertEqual(num_request, init_num_request + 2)
        self.assertEqual(requests[-2].status, CLOSED)
        self.assertNotEqual(requests[-1].status, CLOSED)

    @patch('orchestra.bots.staffbot.send_mail')
    @patch('orchestra.bots.staffbot.message_experts_slack_group')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_restaff_command(self, mock_slack, mock_experts_slack, mock_mail):
        """
        Test that the restaffing logic is properly executed for the
        restaff command.
        """
        task = (Task.objects
                .filter(status=Task.Status.AWAITING_PROCESSING)
                .first())

        # Get certified worker
        task = assign_task(self.worker.id, task.id)
        command = 'restaff {} {}'.format(task.id, self.worker.user.username)

        worker = self.workers[3]
        self._test_staffing_requests(worker, task, command,
                                     can_slack=False, can_mail=True)
        self.assertTrue(mock_mail.called)
        self.assertTrue(mock_experts_slack.called)
        self.assertTrue(mock_slack.called)

    def test_restaff_command_errors(self):
        """
        Test that the staffing logic errors are raised during
        staff command.
        """
        bot = StaffBot()
        command = 'restaff 999999999999 unknown'
        data = get_mock_slack_data(
            text=command,
            user_id=self.worker.slack_user_id)

        response = bot.dispatch(data)
        self.assertEqual(response.get('text'),
                         command)

        self.assertEqual(response['attachments'][0]['text'],
                         bot.worker_does_not_exist.format('unknown'))

        worker = WorkerFactory(user__username='username')
        data['text'] = 'restaff 999999999999 username'
        response = bot.dispatch(data)
        self.assertEqual(response['attachments'][0]['text'],
                         bot.task_does_not_exist_error.format('999999999999'))

        # making sure it works with slack username as well.
        worker.slack_username = 'slackusername'
        worker.save()
        data['text'] = 'restaff 999999999999 slackusername'
        response = bot.dispatch(data)
        self.assertEqual(response['attachments'][0]['text'],
                         bot.task_does_not_exist_error.format('999999999999'))

        data['text'] = 'restaff'
        response = bot.dispatch(data)
        self.assertTrue(bot.default_error_text in response.get('text'))

        task = TaskFactory(status=Task.Status.COMPLETE)
        command = 'restaff {} {}'.format(task.id, worker.user.username)

        data['text'] = command
        response = bot.dispatch(data)
        self.assertEqual(response['attachments'][0]['text'],
                         (bot.task_assignment_does_not_exist_error
                          .format(worker.user.username, task.id)))

    @patch('orchestra.bots.staffbot.send_mail')
    @patch('orchestra.bots.staffbot.message_experts_slack_group')
    @patch('orchestra.bots.staffbot.StaffBot._send_staffing_request_by_slack')
    def test_restaff_close_requests(self, mock_slack,
                                    mock_experts_slack, mock_mail):
        """
        Test that existing staffbot requests for a task is closed when
        a staff function is called.
        """
        CLOSED = StaffBotRequest.Status.CLOSED.value

        bot = StaffBot()
        task = (Task.objects
                .filter(status=Task.Status.AWAITING_PROCESSING)
                .first())
        task = assign_task(self.worker.id, task.id)

        init_num_request = StaffBotRequest.objects.filter(task=task).count()
        self.assertEqual(init_num_request, 0)

        bot.restaff(task.id, self.worker.user.username)
        requests = StaffBotRequest.objects.filter(task=task)
        num_request = requests.count()
        self.assertEqual(num_request, init_num_request + 1)
        self.assertNotEqual(requests.last().status, CLOSED)

        # Calling restaff on the same task should close the previous request
        # and create a new one.
        bot.restaff(task.id, self.worker.user.username)
        requests = list(StaffBotRequest.objects.filter(task=task))
        num_request = len(requests)
        self.assertEqual(num_request, init_num_request + 2)
        self.assertEqual(requests[-2].status, CLOSED)
        self.assertNotEqual(requests[-1].status, CLOSED)

    @override_settings(ORCHESTRA_MOCK_EMAILS=True)
    @patch('orchestra.bots.staffbot.send_mail')
    def test_get_staffing_request_messsage(self, mock_mail):
        def _task_factory(status, path):
            description_no_kwargs = {'path': path}
            return TaskFactory(
                status=status,
                step=StepFactory(
                    slug='stepslug',
                    description='the step',
                    detailed_description_function=description_no_kwargs),
                project__workflow_version__workflow__description=(
                    'the workflow'),
                project__short_description='the coolest project'
            )

        # Test slack without review and with a detailed_description_function
        task = _task_factory(
            Task.Status.AWAITING_PROCESSING,
            'orchestra.tests.helpers.fixtures.get_detailed_description')
        staffing_request_inquiry = StaffingRequestInquiryFactory(
            communication_preference__worker__user__first_name='test-name',
            request__task=task)
        message = StaffBot()._get_staffing_request_message(
            staffing_request_inquiry,
            'communication/new_task_available_slack.txt')
        self.assertEqual(message,
                         '''Hello test-name!

A new task is available for you to work on, if you'd like!  Here are the details:

Project: the workflow
Project description: the coolest project
Task: the step
Details: No text given stepslug

<http://127.0.0.1:8000/orchestra/communication/accept_staffing_request_inquiry/{}/|Accept the Task>
<http://127.0.0.1:8000/orchestra/communication/reject_staffing_request_inquiry/{}/|Ignore the Task>
<http://127.0.0.1:8000/orchestra/communication/available_staffing_requests/|View All Available Tasks>

'''.format(staffing_request_inquiry.id, staffing_request_inquiry.id))  # noqa

        # Test email with review and no detailed_description_function
        task = _task_factory(
            Task.Status.PENDING_REVIEW,
            'orchestra.bots.tests.test_staffbot._noop_details')
        staffing_request_inquiry = StaffingRequestInquiryFactory(
            communication_preference__worker__user__first_name='test-name2',
            request=StaffBotRequestFactory(
                task=task, required_role_counter=1))
        message = StaffBot()._get_staffing_request_message(
            staffing_request_inquiry,
            'communication/new_task_available_email.txt')
        self.assertEqual(message,
                         '''Hello test-name2!

A new task is available for you to work on, if you'd like!  Here are the details:

Project: the workflow
Project description: the coolest project
Task: the step [Review]


<a href="http://127.0.0.1:8000/orchestra/communication/accept_staffing_request_inquiry/{}/">Accept the Task</a>
<a href="http://127.0.0.1:8000/orchestra/communication/reject_staffing_request_inquiry/{}/">Ignore the Task</a>
<a href="http://127.0.0.1:8000/orchestra/communication/available_staffing_requests/">View All Available Tasks</a>

'''.format(staffing_request_inquiry.id, staffing_request_inquiry.id))  # noqa

        # Test that we markdown things
        StaffBot()._send_staffing_request_by_mail('test@test.com', message)
        mock_mail.assert_called_once_with(
            'A new task is available for you',
            message,
            settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL,
            ['test@test.com'],
            html_message=html_from_plaintext(message)
        )
