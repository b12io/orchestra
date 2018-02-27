import logging
import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.template.loader import render_to_string

from orchestra.bots.basebot import BaseBot
from orchestra.bots.errors import SlackUserUnauthorized
from orchestra.communication.errors import SlackError
from orchestra.communication.mail import html_from_plaintext
from orchestra.communication.mail import send_mail
from orchestra.communication.slack import format_slack_message
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import TaskStatusError
from orchestra.models import CommunicationPreference
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.utils.notifications import message_experts_slack_group
from orchestra.utils.task_lifecycle import assert_new_task_status_valid
from orchestra.utils.task_lifecycle import role_counter_required_for_new_task

logger = logging.getLogger(__name__)


# Types of responses we can send to slack
VALID_RESPONSE_TYPES = {'ephemeral', 'in_channel'}

# A regex for markdown links, which are of the form [link text](url).
# We capture link text and url as an text that isn't a closing ] or )
# respectively.
MARKDOWN_LINK_REGEX = re.compile('\[(?P<text>[^\]]*)\]\((?P<url>[^\)]*)\)')


class StaffBot(BaseBot):

    commands = (
        (r'staff\s+(?P<task_id>[0-9]+)', 'staff'),
        (r'restaff\s+(?P<task_id>[0-9]+)\s+(?P<username>[\w.@+-]+)',
         'restaff'),
    )
    task_does_not_exist_error = 'Task {} does not exist'
    task_assignment_error = 'Task {} got an error: "{}"'
    worker_does_not_exist = 'Worker with username {} does not exist'
    nonunique_slack_id = 'There are multiple workers with slack_user_id {}'
    staffing_is_not_allowed = (
        'Staffing of task {} is not allowed at this state')
    task_assignment_does_not_exist_error = (
        'TaskAssignment associated with user {} and task {} does not exist.')
    not_authorized_error = 'You are not authorized to staff projects!'
    staffing_success = 'Got it! I will start staffing task {}!'
    restaffing_success = 'Got it! I will start restaffing task {}!'

    def __init__(self, **kwargs):
        default_config = getattr(settings, 'STAFFBOT_CONFIG', {})
        default_config.update(kwargs)
        token = settings.ORCHESTRA_SLACK_STAFFBOT_TOKEN
        super().__init__(token, **default_config)

    def help(self):
        return format_slack_message(
            'Use `/staffbot` to staff or restaff a Task within Orchestra.',
            attachments=[
                {
                    'pretext': '`/staffbot staff <task-id>`',
                    'text': ('Ask qualified experts to work on'
                             ' the given `<task-id>`.'),
                    'mrkdwn_in': ['text', 'pretext'],
                },
                {
                    'pretext': '`/staffbot restaff <task-id> <username>`',
                    'text': ('Remove the given `<username>` from'
                             ' the task and find another qualified expert'),
                    'mrkdwn_in': ['text', 'pretext'],
                }
            ])

    def staff(self, task_id,
              request_cause=StaffBotRequest.RequestCause.USER.value):
        """
        This function handles staffing a request for the given task_id.
        """
        command = 'staff {}'.format(task_id)
        try:
            task = Task.objects.get(id=task_id)
            required_role_counter = role_counter_required_for_new_task(task)
            error_msg = None
            assert_new_task_status_valid(task.status)
        except TaskStatusError:
            error_msg = self.staffing_is_not_allowed.format(task_id)
        except Task.DoesNotExist:
            error_msg = self.task_does_not_exist_error.format(task_id)
        except TaskAssignmentError as error:
            error_msg = self.task_assignment_error.format(task_id, error)

        if error_msg is not None:
            logger.exception(error_msg)
            return format_slack_message(
                command,
                attachments=[{
                    'color': 'danger',
                    'title': 'Error',
                    'text': error_msg
                }])

        StaffBotRequest.objects.create(
            task=task,
            required_role_counter=required_role_counter,
            request_cause=request_cause)

        slack_message = self.staffing_success.format(task_id)
        message_experts_slack_group(task.project.slack_group_id, slack_message)
        return format_slack_message(
            command,
            attachments=[{
                'color': 'good',
                'title': 'Success',
                'text': slack_message
            }])

    def restaff(self, task_id, username,
                request_cause=StaffBotRequest.RequestCause.USER.value):
        """
        This function handles restaffing a request for the given task_id.
        The current user for the given username is removed, and a new user
        is found.
        """
        command = 'restaff {} {}'.format(task_id, username)
        try:
            error_msg = None

            worker = Worker.objects.filter(
                Q(user__username=username) | Q(slack_username=username))

            if worker.exists():
                worker = worker.first()
            else:
                error_msg = self.worker_does_not_exist.format(username)
                return format_slack_message(
                    command,
                    attachments=[{
                        'color': 'danger',
                        'title': 'Error',
                        'text': error_msg
                    }])
            task = Task.objects.get(id=task_id)
            task_assignment = TaskAssignment.objects.get(worker=worker,
                                                         task=task)
            required_role_counter = task_assignment.assignment_counter

        except Task.DoesNotExist:
            error_msg = self.task_does_not_exist_error.format(task_id)
        except TaskAssignment.DoesNotExist:
            error_msg = (self.task_assignment_does_not_exist_error
                         .format(username, task_id))
        except TaskAssignmentError as error:
            error_msg = self.task_assignment_error.format(task_id, error)

        if error_msg is not None:
            logger.exception(error_msg)
            return format_slack_message(
                command,
                attachments=[{
                    'color': 'danger',
                    'title': 'Error',
                    'text': error_msg
                }])

        StaffBotRequest.objects.create(
            task=task,
            required_role_counter=required_role_counter,
            request_cause=request_cause)
        slack_message = self.restaffing_success.format(task_id)

        message_experts_slack_group(task.project.slack_group_id, slack_message)
        return format_slack_message(
            command,
            attachments=[{
                'color': 'good',
                'title': 'Success',
                'text': slack_message
            }])

    def send_worker_tasks_available_reminder(self, worker):
        communication_type = (
            CommunicationPreference.CommunicationType.NEW_TASK_AVAILABLE.value)

        communication_preference = CommunicationPreference.objects.get(
            communication_type=communication_type,
            worker=worker)

        user = communication_preference.worker.user
        tasks_url = self._get_staffing_url(
            'orchestra:communication:available_staffing_requests',
            None)
        context = {'user': user,
                   'tasks_url': tasks_url}
        if communication_preference.can_email():
            message_body = render_to_string(
                'communication/tasks_available_email.txt',
                context)
            email = communication_preference.worker.user.email
            self._send_staffing_request_by_mail(email, message_body)

        if communication_preference.can_slack():
            message_body = render_to_string(
                'communication/tasks_available_slack.txt',
                context)
            self._send_staffing_request_by_slack(
                communication_preference.worker, message_body)

    def send_task_to_worker(self, worker, staffbot_request):
        """
        Send the task to the worker for them to accept or reject.
        """
        communication_type = (
            CommunicationPreference.CommunicationType.NEW_TASK_AVAILABLE.value)

        communication_preference = CommunicationPreference.objects.get(
            communication_type=communication_type,
            worker=worker)

        if communication_preference.can_email():
            email_method = (
                StaffingRequestInquiry.CommunicationMethod.EMAIL.value)
            staffing_request_inquiry = StaffingRequestInquiry.objects.create(
                communication_preference=communication_preference,
                communication_method=email_method,
                request=staffbot_request)
            message = self._get_staffing_request_message(
                staffing_request_inquiry,
                'communication/new_task_available_email.txt')
            email = communication_preference.worker.user.email
            self._send_staffing_request_by_mail(email, message)

        if communication_preference.can_slack():
            slack_method = (
                StaffingRequestInquiry.CommunicationMethod.SLACK.value)
            staffing_request_inquiry = StaffingRequestInquiry.objects.create(
                communication_preference=communication_preference,
                communication_method=slack_method,
                request=staffbot_request)
            message = self._get_staffing_request_message(
                staffing_request_inquiry,
                'communication/new_task_available_slack.txt')
            self._send_staffing_request_by_slack(
                communication_preference.worker, message)

    def _get_staffing_url(self, reverse_string, url_kwargs):
        return '{}{}'.format(
            settings.ORCHESTRA_URL,
            reverse(reverse_string, kwargs=url_kwargs))

    def get_staffing_request_metadata(self, staffing_request_inquiry):
        url_kwargs = {
            'staffing_request_inquiry_id': staffing_request_inquiry.pk
        }
        accept_url = self._get_staffing_url(
            'orchestra:communication:accept_staffing_request_inquiry',
            url_kwargs)
        reject_url = self._get_staffing_url(
            'orchestra:communication:reject_staffing_request_inquiry',
            url_kwargs)

        # TODO(joshblum): handle urls if present in the detailed_description to
        # convert for slack
        staffbot_request = staffing_request_inquiry.request
        detailed_description = (
            staffbot_request.task.get_detailed_description()
        )
        workflow_description = (
            staffbot_request.task.project
            .workflow_version.workflow.description
        )
        project_description = (
            staffbot_request.task.project
            .short_description
        )
        step_description = (
            staffbot_request.task.step.description)
        user = (staffing_request_inquiry.communication_preference.
                worker.user)
        return {
            'user': user,
            'accept_url': accept_url,
            'reject_url': reject_url,
            'role_counter': staffbot_request.required_role_counter,
            'step_description': step_description,
            'workflow_description': workflow_description,
            'project_description': project_description,
            'detailed_description': detailed_description,
            'task': staffbot_request.task
        }

    def _get_staffing_request_message(self, staffing_request_inquiry,
                                      template):
        context = self.get_staffing_request_metadata(staffing_request_inquiry)
        context['available_requests_url'] = self._get_staffing_url(
            'orchestra:communication:available_staffing_requests', {})
        message_body = render_to_string(template, context)
        return message_body

    def _send_staffing_request_by_mail(self, email, message):
        html_message = html_from_plaintext(message)
        # Slack does not accept html tags, so we want to let markdown add some
        # simple things like <p>
        send_mail('A new task is available for you',
                  message,
                  settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL,
                  [email],
                  html_message=html_message)

    def _send_staffing_request_by_slack(self, worker, message):
        if worker.slack_user_id is None:
            logger.warning('Worker {} does not have a slack id'.format(
                worker))
            return
        try:
            # Replace any Markdown-style links with Slack-style links.
            message = MARKDOWN_LINK_REGEX.sub(r'<\g<url>|\g<text>>', message)
            self.slack.chat.post_message(worker.slack_user_id, message)
        except SlackError:
            logger.warning('Invalid slack id {} {}'.format(
                worker.slack_user_id, message))

    def validate(self, data):
        """
        Handle a request received from slack. First we validate the
        request and then pass the message to the appropriate handler.
        """
        slack_user_id = data.get('user_id')
        username = data.get('user_name')

        workers = Worker.objects.filter(slack_user_id=slack_user_id)
        worker = workers.first()
        if workers.count() > 1:
            raise SlackUserUnauthorized(
                self.nonunique_slack_id.format(slack_user_id))
        elif worker is None:
            raise SlackUserUnauthorized(
                'Worker {} not found. slack_user_id: {}'.format(
                    username, slack_user_id))
        elif not worker.is_project_admin():
            raise SlackUserUnauthorized(self.not_authorized_error)
        data = super().validate(data)
        return data
