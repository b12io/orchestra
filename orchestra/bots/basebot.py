import re

from orchestra.bots.errors import SlackCommandInvalidRequest
from orchestra.bots.errors import BaseBotError
from orchestra.communication.slack import SlackService

# Types of responses we can send to slack
VALID_RESPONSE_TYPES = {'ephemeral', 'in_channel'}


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
        self.slack = SlackService(slack_api_key)
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
        Args:
            text (str):
                Plain text message to send
            attachments (dict):
               See https://api.slack.com/docs/attachments
            response_type (string):
                Should be `in_channel` or `ephemeral`. See
                https://api.slack.com/slash-commands
        Returns:
            formatted_message (dict):
                A formatted message to send via the slack client
        """
        if response_type not in VALID_RESPONSE_TYPES:
            raise BaseBotError(
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
