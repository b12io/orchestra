import logging

from annoying.functions import get_object_or_None
from django.conf import settings
from slacker import Slacker

from orchestra.models import Worker

logger = logging.getLogger(__name__)


def add_worker_slack_ids():
    slack = Slacker(getattr(settings, 'SLACK_EXPERTS_API_KEY', None))
    slack_response = slack.users.list()
    if not slack_response.successful:
        logger.warning('Slack could not be reached.')
        return

    members = slack_response.body.get('members')
    for member in members:
        if member.get('is_bot'):
            continue
        worker = get_object_or_None(Worker,
                                    slack_username=member['name'])
        if worker is None:

            # Try to match user by first name and last name.
            if (member['profile'].get('first_name') is None or
                    member['profile'].get('last_name') is None):
                continue

            workers = Worker.objects.filter(
                user__first_name=member['profile']['first_name'],
                user__last_name=member['profile']['last_name'])
            if workers.count() == 1:
                worker = workers.first()

        if worker:
            logger.info('Username {} has slack id {}'.format(
                member['name'], member['id']))
            worker.slack_id = member['id']
            worker.slack_username = member['name']
            worker.save()
        else:
            logger.info('Could not find worker for username {}'.format(
                member['name']))
