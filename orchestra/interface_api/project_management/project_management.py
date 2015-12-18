from urllib.parse import urljoin

from django.conf import settings
from django.core import urlresolvers
from django.utils import timezone

from orchestra.analytics.latency import work_time_df
from orchestra.models import Project
from orchestra.project_api.api import get_project_information
from orchestra.slack import SlackService
from orchestra.utils.assignment_snapshots import empty_snapshots
from orchestra.utils.task_properties import last_snapshotted_assignment

import logging

logger = logging.getLogger(__name__)


def project_management_information(project_id):
    project = Project.objects.get(id=project_id)
    df = work_time_df([project],
                      human_only=False, complete_tasks_only=False)
    project_information = get_project_information(project.id)
    project_information['project']['status'] = dict(
        Project.STATUS_CHOICES).get(project.status, None)
    project_information['project']['admin_url'] = urljoin(
        settings.ORCHESTRA_URL,
        urlresolvers.reverse(
            'admin:orchestra_project_change',
            args=(project_id,)))

    for slug, task in project_information['tasks'].items():
        task['admin_url'] = urljoin(
            settings.ORCHESTRA_URL,
            urlresolvers.reverse(
                'admin:orchestra_task_change',
                args=(task['id'],)))

        for assignment in task['assignments']:
            assignment['admin_url'] = urljoin(
                settings.ORCHESTRA_URL,
                urlresolvers.reverse(
                    'admin:orchestra_taskassignment_change',
                    args=(assignment['id'],)))

            iterations = df[(df.worker == assignment['worker']['username']) &
                            (df.task_id == task['id'])]
            iterations = iterations[['start_datetime', 'end_datetime']]
            assignment['iterations'] = []
            for idx, info in iterations.T.items():
                iteration = info.to_dict()
                assignment['iterations'].append(iteration)
            if assignment['status'] == 'Processing':
                last_iteration_end = assignment['start_datetime']
                last_assignment = last_snapshotted_assignment(task['id'])
                if last_assignment and len(assignment['iterations']) > 1:
                    last_iteration_end = (
                        last_assignment.snapshots['snapshots'][-1]['datetime'])

                assignment['iterations'].append({
                    'start_datetime': last_iteration_end,
                    'end_datetime': timezone.now()
                })

        if task['status'] in ('Awaiting Processing', 'Pending Review'):
            last_assignment_end = task['start_datetime']
            last_assignment = last_snapshotted_assignment(task['id'])
            if last_assignment:
                last_assignment_end = (
                    last_assignment.snapshots['snapshots'][-1]['datetime'])
            task['assignments'].append({
                'iterations': [{
                    'start_datetime': last_assignment_end,
                    'end_datetime': timezone.now()
                }],
                'snapshots': empty_snapshots(),
                'start_datetime': last_assignment_end,
                'status': 'Processing',
                'task': task['id'],
                'worker': {'id': None, 'username': None},
            })
    return project_information


def edit_slack_membership(project_id, username, action):
    slack = SlackService(settings.SLACK_EXPERTS_API_KEY)
    slack_user_id = slack.users.get_user_id(username)
    slack_group_id = Project.objects.get(id=project_id).slack_group_id
    if action == 'add':
        slack.groups.invite(slack_group_id, slack_user_id)
    elif action == 'remove':
        slack.groups.kick(slack_group_id, slack_user_id)
    else:
        raise Exception('Action not found.')
