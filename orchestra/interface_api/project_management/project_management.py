import logging
from urllib.parse import urljoin

from django.conf import settings
from django import urls
from django.utils import timezone

from orchestra.communication.slack import OrchestraSlackService
from orchestra.models import Project
from orchestra.project_api.api import get_project_information

logger = logging.getLogger(__name__)


def project_management_information(project_id):
    project = Project.objects.get(id=project_id)
    project_information = get_project_information([project.id])
    project_information[project.id]['project']['status'] = dict(
        Project.STATUS_CHOICES).get(project.status, None)
    project_information[project.id]['project']['admin_url'] = urljoin(
        settings.ORCHESTRA_URL,
        urls.reverse(
            'admin:orchestra_project_change',
            args=(project_id,)))

    for slug, task in project_information[project.id]['tasks'].items():
        task['admin_url'] = urljoin(
            settings.ORCHESTRA_URL,
            urls.reverse(
                'admin:orchestra_task_change',
                args=(task['id'],)))

        for assignment in task['assignments']:
            assignment['admin_url'] = urljoin(
                settings.ORCHESTRA_URL,
                urls.reverse(
                    'admin:orchestra_taskassignment_change',
                    args=(assignment['id'],)))

            for iteration in assignment['iterations']:
                iteration['admin_url'] = urljoin(
                    settings.ORCHESTRA_URL,
                    urls.reverse(
                        'admin:orchestra_iteration_change',
                        args=(iteration['id'],)))
                if not iteration['end_datetime']:
                    iteration['end_datetime'] = timezone.now().isoformat()

    return project_information


def edit_slack_membership(project_id, username, action):
    slack = OrchestraSlackService()
    slack_user_id = slack.users.get_user_id(username)
    slack_group_id = Project.objects.get(id=project_id).slack_group_id
    if action == 'add':
        slack.groups.invite(slack_group_id, slack_user_id)
    elif action == 'remove':
        slack.groups.kick(slack_group_id, slack_user_id)
    else:
        raise Exception('Action not found.')
