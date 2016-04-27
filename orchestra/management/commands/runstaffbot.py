import time

from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import autoreload
from slackclient import SlackClient

from orchestra.bots.staffbot import StaffBot
from orchestra.bots.errors import SlackConnectionError


class Command(BaseCommand):
    help = 'Runs a Slack staffbot for RTM calls'

    def handle(self, *args, **options):
        autoreload.main(self.inner_run, None, options)

    def inner_run(self, *args, **options):
        slack_client = SlackClient(settings.STAFFBOT_API_KEY)

        if slack_client.rtm_connect():
            staffbot = StaffBot(slack_client)
            while True:
                staffbot.process_new_messages()
                time.sleep(1)
            pass
        else:
            raise SlackConnectionError('Connection failed. '
                                       'Check if token is valid')
