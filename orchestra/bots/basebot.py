import re

from orchestra.bots.errors import SlackCommandInvalidRequest
from orchestra.communication.slack import format_slack_message
from orchestra.communication.slack import OrchestraSlackService


class BaseBot(object):

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
                 allowed_commands=None,
                 slack_api_key=None,
                 **kwargs):
        """
        Base configuration for the bot to validate messages. If a variable
        is None, all fields are allowed, otherwise each request will only
        be accepted if the request fields are contained in the whitelists.
        """
        self.token = token
        self.slack = OrchestraSlackService(slack_api_key)
        self.whitelists = {
            'team_id': allowed_team_ids,
            'team_domain': allowed_domains,
            'channel_id': allowed_channel_ids,
            'channel_name': allowed_channel_names,
            'user_id': allowed_user_ids,
            'user_name': allowed_user_names,
            'command': allowed_commands,
        }
        self.commands += ((r'help', 'help'),)
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

    def help(self):
        """
        Base classes should implement a description of what the command does.
        """
        raise NotImplementedError

    def no_command_found(self, text):
        """
        If we are unable to parse the command, we return this helpful error
        message.
        """
        return format_slack_message(
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
