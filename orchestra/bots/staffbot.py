from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import render_to_string

from orchestra.bots.basebot import BaseBot
from orchestra.communication.mail import send_mail
from orchestra.models import StaffingRequest
from orchestra.models import Worker
from orchestra.utils.task_lifecycle import is_worker_certified_for_task
from orchestra.utils.task_lifecycle import check_worker_allowed_new_assignment

# Types of responses we can send to slack
VALID_RESPONSE_TYPES = {'ephemeral', 'in_channel'}


class StaffBot(BaseBot):

    commands = (
        (r'staff (?P<task_id>[0-9]+)', 'staff'),
        (r'restaff (?P<task_id>[0-9]+) (?P<username>[\w.@+-]+)', 'restaff'),
    )

    commands = (
        (r'staff (?P<task_id>[0-9]+)', 'staff'),
        (r'restaff (?P<task_id>[0-9]+) (?P<username>[\w.@+-]+)', 'restaff'),
    )

    def __init__(self, **kwargs):
        default_config = getattr(settings, 'STAFFBOT_CONFIG', {})
        default_config.update(kwargs)
        token = settings.SLACK_STAFFBOT_TOKEN
        super().__init__(token, **kwargs)

    def staff(self, task_id):
        """
        This function handles staffing a request for the given task_id.
        """
        return self.format_slack_message('Staffed task {}!'.format(task_id))

    def restaff(self, task_id, username):
        """
        This function handles restaffing a request for the given task_id.
        The current user for the given username is removed, and a new user
        is found.
        """
        return self.format_slack_message(
            'Restaffed task {} for {}!'.format(task_id, username)
        )

    def _send_task_to_workers(self, task, required_role):
        # get all the workers that are certified to complete the task.
        workers = Worker.objects.all()
        # TODO(joshblum): push is_worker_certified_for_task and
        # check_worker_allowed_new_assignment into the DB as filters so we
        # don't loop over all workers
        for worker in workers:
            can_send = (
                is_worker_certified_for_task(worker, task, required_role) and
                check_worker_allowed_new_assignment(worker, task.status)
            )
            if can_send:
                self._send_task_to_worker(
                    worker, task, required_role)

    def _send_task_to_worker(self, worker, task):
        """
        Send the task to the worker for them to accept or reject.
        """
        staffing_request = StaffingRequest.objects.create(
            worker=worker,
            task=task,
            request_cause=StaffingRequest.RequestCause.AUTOSTAFF.value,
            communication_method=(
                StaffingRequest.CommunicationMethod.EMAIL.value))

        url_kwargs = {
            'pk': staffing_request.pk
        }

        accept_url = '{}{}'.format(
            settings.ORCHESTRA_URL,
            reverse('orchestra:communication:accept_staffing_request',
                    kwargs=url_kwargs))

        reject_url = '{}{}'.format(
            settings.ORCHESTRA_URL,
            reverse('orchestra:communication:reject_staffing_request',
                    kwargs=url_kwargs))

        context = Context({
            'username': worker.user.username,
            'accept_url': accept_url,
            'reject_url': reject_url
        })

        message_body = render_to_string('communication/new_task_available.txt',
                                        context)
        send_mail('New task is available for claim',
                  message_body,
                  settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL,
                  [worker.user.email])

        staffing_request.status = StaffingRequest.Status.SENT.value
        staffing_request.save()
