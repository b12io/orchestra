from django.conf import settings

from orchestra.bots.errors import SlackCommandInvalidRequest


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
