import base64
from uuid import uuid1

from django.conf import settings
import slacker

from orchestra.utils.settings import run_if


class SlackService(object):
    """
    Wrapper slack service to allow easy swapping and mocking out of API.
    """
    def __init__(self, api_key):
        self._service = slacker.Slacker(api_key)
        for attr_name in ('chat', 'groups', 'users'):
            setattr(self, attr_name, getattr(self._service, attr_name))


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


def _project_slack_group_name(project):
    """
    Return a unique identifier for project slack groups; must fit into slack's
    21 char limit for group names.
    """
    return base64.b64encode(uuid1().bytes)
