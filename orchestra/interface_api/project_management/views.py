import slacker
from jsonview.exceptions import BadRequest
from rest_framework import generics
from rest_framework import permissions

from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import WorkerCertificationError
from orchestra.interface_api.project_management.decorators import \
    is_project_admin
from orchestra.interface_api.project_management.decorators import \
    project_management_api_view
from orchestra.interface_api.project_management import project_management
from orchestra.models import Task
from orchestra.models import Project
from orchestra.models import Worker
from orchestra.utils.load_json import load_encoded_json
from orchestra.project_api.serializers import ProjectSerializer
from orchestra.utils.revert import revert_task_to_iteration
from orchestra.utils.task_lifecycle import complete_and_skip_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import reassign_assignment
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import end_project


class IsProjectAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return is_project_admin(request.user)


class ProjectList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, IsProjectAdmin)
    serializer_class = ProjectSerializer
    queryset = Project.objects.exclude(status=Project.Status.ABORTED)


@project_management_api_view
def project_information_api(request):
    project_id = load_encoded_json(request.body)['project_id']
    try:
        return project_management.project_management_information(project_id)
    except Project.DoesNotExist:
        raise BadRequest('Project not found for the given id.')


@project_management_api_view
def reassign_assignment_api(request):
    worker_username = load_encoded_json(request.body)['worker_username']
    try:
        worker = Worker.objects.get(user__username=worker_username)
    except Worker.DoesNotExist:
        raise BadRequest('Worker not found for the given username.')
    assignment_id = load_encoded_json(request.body)['assignment_id']

    try:
        reassign_assignment(worker.id, assignment_id)
    except (WorkerCertificationError, TaskAssignmentError) as e:
        raise BadRequest(e)


@project_management_api_view
def revert_task_api(request):
    body = load_encoded_json(request.body)
    try:
        audit = revert_task_to_iteration(
            body['task_id'], body['iteration_id'],
            body.get('revert_before'), body.get('commit'))
    except Task.DoesNotExist as e:
        raise BadRequest(e)
    return audit


@project_management_api_view
def complete_and_skip_task_api(request):
    task_id = load_encoded_json(request.body)['task_id']
    complete_and_skip_task(task_id)


@project_management_api_view
def assign_task_api(request):
    worker_username = load_encoded_json(request.body)['worker_username']
    try:
        worker = Worker.objects.get(user__username=worker_username)
        task_id = load_encoded_json(request.body)['task_id']
        assign_task(worker.id, task_id)
    except (Worker.DoesNotExist,
            Task.DoesNotExist,
            WorkerCertificationError) as e:
        raise BadRequest(e)


@project_management_api_view
def create_subsequent_tasks_api(request):
    project_id = load_encoded_json(request.body)['project_id']
    try:
        project = Project.objects.get(id=project_id)
    except Project.DoesNotExist:
        raise BadRequest('Project not found for the given id.')
    create_subsequent_tasks(project)


@project_management_api_view
def edit_slack_membership_api(request):
    body = load_encoded_json(request.body)
    try:
        project_management.edit_slack_membership(
            body['project_id'], body['username'], body['action'])
    except slacker.Error as e:
        raise BadRequest(e)


@project_management_api_view
def end_project_api(request):
    project_id = load_encoded_json(request.body)['project_id']
    try:
        end_project(project_id)
    except Project.DoesNotExist:
        raise BadRequest('Project not found for the given id.')
