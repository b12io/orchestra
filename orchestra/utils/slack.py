from django.conf import settings
from slacker import Slacker as _Slacker


class Slacker(_Slacker):
    def __init__(self):
        super().__init__(settings.SLACK_EXPERTS_API_KEY)


def get_slack_user_id(slack_username):
    slack = Slacker()
    slack_user_id = slack.users.get_user_id(slack_username)
    return slack_user_id
