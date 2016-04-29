from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import render_to_string

from orchestra.bots.errors import SlackCommandInvalidRequest
from orchestra.communication.mail import send_mail
from orchestra.models import StaffingRequest
from orchestra.models import Worker
from orchestra.utils.task_lifecycle import is_worker_certified_for_task
from orchestra.utils.task_lifecycle import check_worker_allowed_new_assignment


class Bot(object):

    def __init__(self, token,
                 allowed_team_ids=None,
                 allowed_domains=None,
                 allowed_channel_ids=None,
                 allowed_channel_names=None,
                 allowed_user_ids=None,
                 allowed_user_names=None,
                 allowed_commands=None):
        """
            Base configuration for the bot to validate messages. If a variable
            is None, all fields are allowed, otherwise each request will only
            be accepted if the request fields are contained in the whitelists.
        """
        self.token = token
        self.whitelists = {
            'team_id': allowed_team_ids,
            'team_domain': allowed_domains,
            'channel_id': allowed_channel_ids,
            'channel_name': allowed_channel_names,
            'user_id': allowed_user_ids,
            'user_name': allowed_user_names,
            'command': allowed_commands,
        }

    def validate(self, data):
        """
            Handle a request received from slack. First we validate the
            request and then pass the message to the appropriate handler.
        """
        token = data.get('token')
        if token != self.token:
            raise SlackCommandInvalidRequest(
                'Token mismatch {} != {}'.format(token, self.token))

        for fieldname, whitelist in self.whitelists.items():
            if whitelist is None:
                continue
            else:
                if hasattr(data, fieldname):
                    value = data[fieldname]
                else:
                    raise SlackCommandInvalidRequest(
                        '{} is missing'.format(fieldname))

                if value not in whitelist:
                    raise SlackCommandInvalidRequest(
                        'Field {} did not validate: {}'.format(
                            fieldname, value))
        return data

    def dispatch(self, data):
        """
            Method to pass data for processing. Should return a dictionary of
            data to return to the user.
        """
        raise NotImplementedError


class StaffBot(Bot):

    def __init__(self, **kwargs):
        default_config = getattr(settings, 'STAFFBOT_CONFIG', {})
        default_config.update(kwargs)
        token = settings.SLACK_STAFFBOT_TOKEN
        super().__init__(token, **kwargs)

    def dispatch(self, data):
        data = self.validate(data)
        return {'text': data.get('text')}

    def _send_task_to_workers(self, task, required_role):
        # get all the workers that are certified to complete the task.
        workers = Worker.objects.all()

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
            Send the task to the worker for them to accept or reject
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
