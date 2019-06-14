import logging
import random
import string

from django.conf import settings
from django.utils.text import slugify

from requests.exceptions import HTTPError

from slacker import Error as SlackError
from slacker import BaseAPI
from slacker import Slacker

from orchestra.communication.errors import SlackFormatError
from orchestra.utils.decorators import run_if

logger = logging.getLogger(__name__)

# Types of responses we can send to slack
VALID_RESPONSE_TYPES = {'ephemeral', 'in_channel'}
_request = BaseAPI._request


def _silent_request(*args, **kwargs):
    """
    Attempt to make Slack API request and ignore if an exception is thrown.

    TODO(jrbotros): this silences all errors, but we likely will want to be
    able to surface errors in some cases in the future
    """
    try:
        return _request(*args, **kwargs)
    except SlackError:
        logger.exception('Slack API Error')
    except HTTPError as e:
        status_code = e.response.status_code
        # If we're being rate-limited, log the exception but don't fail.
        if status_code == 429:
            logger.exception('Slack API rate limit')
        else:
            raise


BaseAPI._request = _silent_request


class OrchestraSlackService(object):
    """
    Wrapper slack service to allow easy swapping and mocking out of API.
    """

    def __init__(self, api_key=None):
        if not api_key:
            api_key = settings.SLACK_EXPERTS_API_KEY
        self._service = Slacker(api_key)
        for attr_name in ('chat', 'groups', 'users'):
            setattr(self, attr_name, getattr(self._service, attr_name))


@run_if('ORCHESTRA_SLACK_EXPERTS_ENABLED')
def get_slack_user_id(slack_username):
    slack = OrchestraSlackService()
    slack_user_id = slack.users.get_user_id(slack_username)
    return slack_user_id


@run_if('ORCHESTRA_SLACK_EXPERTS_ENABLED')
def add_worker_to_project_team(worker, project):
    slack = OrchestraSlackService()
    try:
        user_id = slack.users.get_user_id(worker.slack_username)
        response = slack.groups.invite(project.slack_group_id, user_id)
        if not response.body.get('already_in_group'):
            welcome_message = (
                '<@{}|{}> has been added to the team. '
                'Welcome aboard!').format(user_id, worker.slack_username)
            slack.chat.post_message(project.slack_group_id, welcome_message)
    except SlackError:
        logger.exception('Slack API Error')
        # TODO(jrbotros): for now, using slack on a per-worker basis is
        # optional; we'll want to rethink this in the future


@run_if('ORCHESTRA_SLACK_EXPERTS_ENABLED')
def create_project_slack_group(project):
    """
    Create slack channel for project team communication
    """
    slack = OrchestraSlackService()
    response = slack.groups.create(_project_slack_group_name(project))
    project.slack_group_id = response.body['group']['id']
    slack.groups.set_topic(project.slack_group_id, project.short_description)
    slack.groups.set_purpose(project.slack_group_id,
                             'Discussing work on `{}`'.format(
                                 project.short_description))
    project.save()

    # Message out project folder id.
    if project.project_data.get('project_folder_id'):
        message = (
            'Project folder: '
            'https://drive.google.com/drive/folders/{}'
        ).format(project.project_data['project_folder_id'])
        slack.chat.post_message(project.slack_group_id, message)
    return project.slack_group_id


@run_if('ORCHESTRA_SLACK_EXPERTS_ENABLED')
def archive_project_slack_group(project):
    """
    Archive a slack channel of a project
    """
    slack = OrchestraSlackService()
    try:
        response = slack.groups.archive(project.slack_group_id)
        if response:
            is_archived = response.body.get('ok')
            if not is_archived:
                logger.error('Archive project error: %s',
                             response.body.get('error'))
    except SlackError:
        logger.exception('Slack API Error')


@run_if('ORCHESTRA_SLACK_EXPERTS_ENABLED')
def unarchive_project_slack_group(project):
    """
    Unarchive a slack channel of a project
    """
    slack = OrchestraSlackService()
    try:
        group_info = slack.groups.info(project.slack_group_id)
        is_archived = group_info.body.get('group', {}).get('is_archived')
        if is_archived:
            response = slack.groups.unarchive(project.slack_group_id)
            if response:
                is_unarchived = response.body.get('ok')
                if not is_unarchived:
                    logger.error('Unarchive project error: %s',
                                 response.body.get('error'))
    except SlackError:
        logger.exception('Slack API Error')


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
    slack = OrchestraSlackService()
    groups = {group['name'] for group in slack.groups.list().body['groups']}
    while True:
        # Add 4 characters of randomness (~1.68 million permutations).
        name = '{}-{}'.format(descriptor, _random_string())
        if name not in groups:
            break
    return name


def format_slack_message(text,
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
        raise SlackFormatError(
            'Response type {} is invalid'.format(response_type))
    return {
        'response_type': response_type,
        'text': text,
        'attachments': attachments,
    }
