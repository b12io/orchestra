import json

import slacker
from django.contrib.auth.decorators import login_required
from django.contrib.auth.decorators import user_passes_test
from jsonview.decorators import json_view
from jsonview.exceptions import BadRequest

from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import WorkerCertificationError
from orchestra.models import Task
from orchestra.models import Project
from orchestra.models import Worker
from orchestra.utils.revert import revert_task_to_iteration
from orchestra.utils.task_lifecycle import complete_and_skip_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import reassign_assignment
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import end_project

from orchestra.interface_api.project_management import project_management

import logging

logger = logging.getLogger(__name__)


def is_project_admin(user):
    return user.groups.filter(name='project_admins').exists()


@json_view
@login_required
@user_passes_test(is_project_admin)
def project_information_api(request):
    project_id = json.loads(request.body.decode())['project_id']
    try:
        return project_management.project_management_information(project_id)
    except Project.DoesNotExist:
        raise BadRequest('Project not found for the given id.')


@json_view
@login_required
@user_passes_test(is_project_admin)
def reassign_assignment_api(request):
    worker_username = json.loads(request.body.decode())['worker_username']
    try:
        worker = Worker.objects.get(user__username=worker_username)
    except Worker.DoesNotExist:
        raise BadRequest('Worker not found for the given username.')
    assignment_id = json.loads(request.body.decode())['assignment_id']

    try:
        reassign_assignment(worker.id, assignment_id)
    except (WorkerCertificationError, TaskAssignmentError) as e:
        raise BadRequest(e)


@json_view
@login_required
@user_passes_test(is_project_admin)
def revert_task_api(request):
    body = json.loads(request.body.decode())
    try:
        audit = revert_task_to_iteration(
            body['task_id'], body['iteration_id'],
            body.get('revert_before'), body.get('commit'))
    except Task.DoesNotExist as e:
        raise BadRequest(e)
    return audit


@json_view
@login_required
@user_passes_test(is_project_admin)
def complete_and_skip_task_api(request):
    task_id = json.loads(request.body.decode())['task_id']
    complete_and_skip_task(task_id)


@json_view
@login_required
@user_passes_test(is_project_admin)
def assign_task_api(request):
    worker_username = json.loads(request.body.decode())['worker_username']
    try:
        worker = Worker.objects.get(user__username=worker_username)
        task_id = json.loads(request.body.decode())['task_id']
        assign_task(worker.id, task_id)
    except (Worker.DoesNotExist,
            Task.DoesNotExist,
            WorkerCertificationError) as e:
        raise BadRequest(e)


@json_view
@login_required
@user_passes_test(is_project_admin)
def create_subsequent_tasks_api(request):
    project_id = json.loads(request.body.decode())['project_id']
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise BadRequest('Project not found for the given id.')
    create_subsequent_tasks(project)


@json_view
@login_required
@user_passes_test(is_project_admin)
def edit_slack_membership_api(request):
    body = json.loads(request.body.decode())
    try:
        project_management.edit_slack_membership(
            body['project_id'], body['username'], body['action'])
    except slacker.Error as e:
        raise BadRequest(e)


@json_view
@login_required
@user_passes_test(is_project_admin)
def end_project_api(request):
    project_id = json.loads(request.body.decode())['project_id']
    try:
        end_project(project_id)
    except Project.DoesNotExist:
        raise BadRequest('Project not found for the given id.')
