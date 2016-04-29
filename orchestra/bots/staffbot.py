import re

from django.conf import settings
from django.core.urlresolvers import reverse
from django.template import Context
from django.template.loader import render_to_string

from orchestra.bots.errors import SlackCommandInvalidRequest
from orchestra.bots.errors import BotError
from orchestra.communication.mail import send_mail
from orchestra.models import StaffingRequest
from orchestra.models import Worker
from orchestra.utils.task_lifecycle import is_worker_certified_for_task
from orchestra.utils.task_lifecycle import check_worker_allowed_new_assignment

# Types of responses we can send to slack
VALID_RESPONSE_TYPES = {'ephemeral', 'in_channel'}


class Bot(object):

    # Tuple of (pattern, command_function_string) to match commands to
    commands = ()
    default_error_text = 'Sorry! We couldn\'t process your command'

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
        is `None`, all fields are allowed, otherwise each request will only
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
        self.command_matchers = [
            (re.compile(pattern, re.IGNORECASE), command)
            for pattern, command in self.commands
        ]

    def validate(self, data):
        """
        Handle a request received from slack. First we validate the
        request and then pass the message to the appropriate handler.
        """
        token = data.get('token')
        if token != self.token:
            raise SlackCommandInvalidRequest('Invalid token.')

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

    def format_slack_message(self, text,
                             attachments=None,
                             response_type='ephemeral'):
        """
        Helper method to send back a response in response to the slack user.
        `text` is plain text to be sent, `attachments` is a dictionary of
        further data to attach to the message. See
        https://api.slack.com/docs/attachments
        """
        if response_type not in VALID_RESPONSE_TYPES:
            raise BotError(
                'Response type {} is invalid'.format(response_type))

        return {
            'response_type': response_type,
            'text': text,
            'attachments': attachments,
        }

    def no_command_found(self, text):
        """
        If we are unable to parse the command, we return this helpful error
        message.
        """
        return self.format_slack_message(
            '{}: {}'.format(self.default_error_text, text)
        )

    def _find_command(self, text):
        for matcher, command_fn in self.command_matchers:
            match = matcher.match(text)
            if match is not None:
                return getattr(self, command_fn), match.groupdict()

        # If we don't match anything, at least let the user know.
        return self.no_command_found, {'text': text}

    def dispatch(self, data):
        """
        Method to pass data for processing. Should return a dictionary of
        data to return to the user.
        """
        data = self.validate(data)
        text = data.get('text')

        command_fn, kwargs = self._find_command(text)
        return command_fn(**kwargs)


class StaffBot(Bot):

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
