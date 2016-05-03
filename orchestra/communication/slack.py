import random
import string

from django.conf import settings
from django.utils.text import slugify
from orchestra.utils.settings import run_if
from slacker import Slacker

import logging

logger = logging.getLogger(__name__)


class SlackService(object):
    """
    Wrapper slack service to allow easy swapping and mocking out of API.
    """

    def __init__(self, api_key=None):
        if not api_key:
            api_key = settings.SLACK_EXPERTS_API_KEY
        self._service = Slacker(api_key)
        for attr_name in ('chat', 'groups', 'users'):
            setattr(self, attr_name, getattr(self._service, attr_name))

    def post_message(self, slack_user_id, message, parse='none'):
        if settings.PRODUCTION:
            self.chat.post_message(
                slack_user_id, message, parse=parse)
        else:
            logger.info('{}: {}'.format(slack_user_id, message))


def get_slack_user_id(slack_username):
    slack = SlackService()
    slack_user_id = slack.users.get_user_id(slack_username)
    return slack_user_id


@run_if('SLACK_EXPERTS')
def add_worker_to_project_team(worker, project):
    slack = SlackService(settings.SLACK_EXPERTS_API_KEY)
    try:
        user_id = slack.users.get_user_id(worker.slack_username)
        response = slack.groups.invite(project.slack_group_id, user_id)
        if not response.body.get('already_in_group'):
            welcome_message = (
                '<@{}|{}> has been added to the team. '
                'Welcome aboard!').format(user_id, worker.slack_username)
            slack.chat.post_message(project.slack_group_id, welcome_message)
    except:
        # TODO(jrbotros): for now, using slack on a per-worker basis is
        # optional; we'll want to rethink this in the future
        pass


@run_if('SLACK_EXPERTS')
def create_project_slack_group(project):
    """
    Create slack channel for project team communication
    """
    slack = SlackService(settings.SLACK_EXPERTS_API_KEY)
    response = slack.groups.create(_project_slack_group_name(project))
    project.slack_group_id = response.body['group']['id']
    slack.groups.set_topic(project.slack_group_id, project.short_description)
    slack.groups.set_purpose(project.slack_group_id,
                             'Discussing work on `{}`'.format(
                                 project.short_description))
    project.save()
    return project.slack_group_id


def _random_string():
    return ''.join(
        random.choice(string.ascii_lowercase + string.digits)
        for idx in range(4))


def _project_slack_group_name(project):
    """
    Return a unique and readable identifier for project slack groups.

    Slack group names are capped at 21 characters in length.
    """
    name = None
    # The human-readable portion of the name (16 characters) involves
    # slugifying the project short description.
    descriptor = slugify(project.short_description)[:16].strip('-')
    slack = SlackService(settings.SLACK_EXPERTS_API_KEY)
    groups = {group['name'] for group in slack.groups.list().body['groups']}
    while True:
        # Add 4 characters of randomness (~1.68 million permutations).
        name = '{}-{}'.format(descriptor, _random_string())
        if name not in groups:
            break
    return name
