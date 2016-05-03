from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import render_to_string

from orchestra.bots.basebot import BaseBot
from orchestra.communication.mail import send_mail
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import TaskStatusError
from orchestra.models import CommunicationPreference
from orchestra.models import StaffingRequest
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.utils.task_lifecycle import remove_worker_from_task
from orchestra.utils.task_lifecycle import role_required_for_new_task
from orchestra.utils.task_lifecycle import is_worker_certified_for_task
from orchestra.utils.task_lifecycle import check_worker_allowed_new_assignment

import logging

logger = logging.getLogger(__name__)


# Types of responses we can send to slack
VALID_RESPONSE_TYPES = {'ephemeral', 'in_channel'}


class StaffBot(BaseBot):

    commands = (
        (r'staff (?P<task_id>[0-9]+)', 'staff'),
        (r'restaff (?P<task_id>[0-9]+) (?P<username>[\w.@+-]+)', 'restaff'),
    )
    task_does_not_exist_error = 'Task {} does not exist'
    task_assignment_error = 'Task {} got an error: "{}"'
    worker_does_not_exist = 'Worker with username {} does not exist'
    task_assignment_does_not_exist_error = (
        'TaskAssignment associated with user {} and task {} does not exist.')

    def __init__(self, **kwargs):
        default_config = getattr(settings, 'STAFFBOT_CONFIG', {})
        default_config.update(kwargs)
        token = settings.SLACK_STAFFBOT_TOKEN
        super().__init__(token, **kwargs)

    def help(self):
        return self.format_slack_message(
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
              request_cause=StaffingRequest.RequestCause.USER.value):
        """
        This function handles staffing a request for the given task_id.
        """
        try:
            task = Task.objects.get(id=task_id)
            required_role = role_required_for_new_task(task)
            error_msg = None
        except Task.DoesNotExist:
            error_msg = self.task_does_not_exist_error.format(task_id)
        except TaskAssignmentError as error:
            error_msg = self.task_assignment_error.format(task_id, error)
        if error_msg is not None:
            logger.exception(error_msg)
            return self.format_slack_message(error_msg)
        self._send_task_to_workers(task, required_role, request_cause)
        return self.format_slack_message('Staffed task {}!'.format(task_id))

    def restaff(self, task_id, username,
                request_cause=StaffingRequest.RequestCause.USER.value):
        """
        This function handles restaffing a request for the given task_id.
        The current user for the given username is removed, and a new user
        is found.
        """
        # TODO(kkamalov): maybe username could also be slack_username
        try:
            task = remove_worker_from_task(username, task_id)
            required_role = role_required_for_new_task(task)
            error_msg = None
        except Worker.DoesNotExist:
            error_msg = self.worker_does_not_exist.format(username)
        except Task.DoesNotExist:
            error_msg = self.task_does_not_exist_error.format(task_id)
        except TaskAssignment.DoesNotExist:
            error_msg = (self.task_assignment_does_not_exist_error
                         .format(username, task_id))
        except TaskAssignmentError as error:
            error_msg = self.task_assignment_error.format(task_id, error)

        if error_msg is not None:
            logger.exception(error_msg)
            return self.format_slack_message(error_msg)
        self._send_task_to_workers(
            task, required_role, request_cause)
        return self.format_slack_message('Restaffed task {}!'.format(task_id))

    def _send_task_to_workers(self, task, required_role, request_cause):
        # get all the workers that are certified to complete the task.
        workers = Worker.objects.all()
        # TODO(joshblum): push is_worker_certified_for_task and
        # check_worker_allowed_new_assignment into the DB as filters so we
        # don't loop over all workers
        for worker in workers:
            try:
                check_worker_allowed_new_assignment(worker, task.status)
                if is_worker_certified_for_task(worker, task, required_role):
                    self._send_task_to_worker(
                        worker, task, required_role, request_cause)
            except TaskStatusError:
                pass
            except TaskAssignmentError:
                pass

    def _send_task_to_worker(self, worker, task, required_role, request_cause):
        """
        Send the task to the worker for them to accept or reject.
        """
        communication_type = (
            CommunicationPreference.CommunicationType.NEW_TASK_AVAILABLE.value)

        communication_preference = CommunicationPreference.objects.get(
            communication_type=communication_type,
            worker=worker)

        if communication_preference.can_email():
            email_method = StaffingRequest.CommunicationMethod.EMAIL.value
            staffing_request = StaffingRequest.objects.create(
                communication_preference=communication_preference,
                task=task,
                required_role=required_role,
                request_cause=request_cause,
                communication_method=email_method)
            message = self._get_staffing_request_message(
                staffing_request, 'communication/new_task_available_email.txt')
            self._send_staffing_request_by_mail(staffing_request, message)

        if communication_preference.can_slack():
            slack_method = StaffingRequest.CommunicationMethod.SLACK.value
            staffing_request = StaffingRequest.objects.create(
                communication_preference=communication_preference,
                task=task,
                required_role=required_role,
                request_cause=request_cause,
                communication_method=slack_method)
            message = self._get_staffing_request_message(
                staffing_request, 'communication/new_task_available_slack.txt')
            self._send_staffing_request_by_slack(staffing_request, message)

    def _get_staffing_url(self, reverse_string, url_kwargs):
        return '{}{}'.format(
            settings.ORCHESTRA_URL,
            reverse(reverse_string, kwargs=url_kwargs))

    def _get_staffing_request_message(self, staffing_request, template):
        username = (
            staffing_request.communication_preference.worker.user.username)

        url_kwargs = {
            'staffing_request_id': staffing_request.pk
        }
        accept_url = self._get_staffing_url(
            'orchestra:communication:accept_staffing_request', url_kwargs)
        reject_url = self._get_staffing_url(
            'orchestra:communication:reject_staffing_request', url_kwargs)

        roles = dict(WorkerCertification.ROLE_CHOICES)
        context = Context({
            'username': username,
            'accept_url': accept_url,
            'reject_url': reject_url,
            'required_role': roles.get(staffing_request.required_role)
        })

        message_body = render_to_string(template, context)
        return message_body

    def _send_staffing_request_by_mail(self, staffing_request, message):
        email = (
            staffing_request.communication_preference.worker.user.email)

        send_mail('New task is available for claim',
                  message,
                  settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL,
                  [email])
        staffing_request.status = StaffingRequest.Status.SENT.value
        staffing_request.save()

    def _send_staffing_request_by_slack(self, staffing_request, message):
        worker = (
            staffing_request.communication_preference.worker)
        if worker.slack_user_id is None:
            logger.error('Worker {} does not have a slack id'.format(
                worker))
            return

        self.slack.post_message(worker.slack_user_id, message)
        staffing_request.status = StaffingRequest.Status.SENT.value
        staffing_request.save()
