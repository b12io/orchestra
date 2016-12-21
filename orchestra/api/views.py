import slacker
from jsonview.exceptions import BadRequest
from rest_framework.viewsets import ModelViewSet
from rest_framework.decorators import detail_route
from orchestra.core.errors import IllegalTaskSubmission
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import TimerError
from orchestra.core.errors import WorkerCertificationError
from orchestra.interface_api.project_management import project_management
from orchestra.models.core.models import Iteration
from orchestra.models.core.models import Project
from orchestra.models.core.models import TaskAssignment
from orchestra.models.core.models import Task
from orchestra.models.core.models import TimeEntry
from orchestra.models.core.models import Worker
from orchestra.models.core.models import WorkerCertification
from orchestra.project_api.serializers import IterationSerializer
from orchestra.project_api.serializers import ProjectSerializer
from orchestra.project_api.serializers import TaskAssignmentSerializer
from orchestra.project_api.serializers import TaskSerializer
from orchestra.project_api.serializers import TaskTimerSerializer
from orchestra.project_api.serializers import TimeEntrySerializer
from orchestra.project_api.serializers import WorkerCertificationSerializer
from orchestra.project_api.serializers import WorkerSerializer
from orchestra.utils import time_tracking
from orchestra.utils.revert import revert_task_to_iteration
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import complete_and_skip_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import end_project
from orchestra.utils.task_lifecycle import reassign_assignment
from orchestra.utils.task_lifecycle import submit_task


import logging
logger = logging.getLogger(__name__)


class IterationViewSet(ModelViewSet):
    serializer_class = IterationSerializer

    def get_queryset(self):
        return Iteration.objects.all()


class ProjectViewSet(ModelViewSet):
    serializer_class = ProjectSerializer

    def get_queryset(self):
        return Project.objects.all()

    @detail_route(methods=['POST'])
    def abort(self, request, pk=None):
        try:
            end_project(self.get_object().id)
        except Project.DoesNotExist as e:
            raise BadRequest(e)

    @detail_route(methods=['POST'])
    def add_slack_user(self, request, pk=None):
        try:
            # TODO(jrbotros): don't use strings to specify add/remove
            project_management.edit_slack_membership(
                self.get_object.id(), request.data['username'], 'add')
        except slacker.Error as e:
            raise BadRequest(e)

    @detail_route(methods=['POST'])
    def remove_slack_user(self, request, pk=None):
        try:
            # TODO(jrbotros): don't use strings to specify add/remove
            project_management.edit_slack_membership(
                self.get_object.id(), request.data['username'], 'remove')
        except slacker.Error as e:
            raise BadRequest(e)

    @detail_route(methods=['POST'])
    def create_subsequent_tasks(self, request, pk=None):
        try:
            project = Project.objects.get(id=self.get_object().id)
            create_subsequent_tasks(project)
        except Project.DoesNotExist:
            raise BadRequest('Project not found for the given id.')


class TaskViewSet(ModelViewSet):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.all()

    @detail_route(methods=['POST'])
    def assign(self, request, pk=None):
        try:
            # TODO(jrbotros): should this take something other than username?
            worker = Worker.objects.get(
                user__username=request.data['worker_username'])
            assign_task(worker.id, self.get_object().id)
        except (Worker.DoesNotExist,
                Task.DoesNotExist,
                WorkerCertificationError) as e:
            raise BadRequest(e)

    @detail_route(methods=['POST'])
    def submit(self, request, pk=None):
        self._submit_task(request, Iteration.Status.REQUESTED_REVIEW)

    @detail_route(methods=['POST'])
    def reject(self, request, pk=None):
        self._submit_task(request, Iteration.Status.PROVIDED_REVIEW)

    @detail_route(methods=['POST'])
    def skip(self, request, pk=None):
        complete_and_skip_task(self.get_object().id)

    @detail_route(methods=['POST'])
    def revert(self, request, pk=None):
        try:
            return revert_task_to_iteration(
                self.get_object().id, request.data['iteration_id'],
                request.data.get('revert_before'), request.data.get('commit'))
        except Task.DoesNotExist as e:
            raise BadRequest(e)

    def _submit_task(self, request, iteration_status):
        if request.data.get('worker'):
            worker = Worker.objects.get(id=request.data['worker'])
        else:
            worker = Worker.objects.get(user=request.user)
        try:
            return submit_task(
                self.get_object().id, request.data['task_data'],
                iteration_status, worker)
        except TaskStatusError:
            raise BadRequest('Task already completed.')
        except Task.DoesNotExist:
            raise BadRequest('No task for given id.')
        except IllegalTaskSubmission as e:
            raise BadRequest(e)
        except TaskAssignmentError as e:
            raise BadRequest(e)


class TaskAssignmentViewSet(ModelViewSet):
    serializer_class = TaskAssignmentSerializer

    def get_queryset(self):
        return TaskAssignment.objects.all()

    @detail_route(methods=['POST'])
    def reassign(self, request, pk=None):
        # TODO(jrbotros): should this take something other than username?
        try:
            worker = Worker.objects.get(
                user__username=request.data['worker_username'])
        except Worker.DoesNotExist:
            raise BadRequest('Worker not found for the given username.')
        try:
            reassign_assignment(worker.id, self.get_object().id)
        except (WorkerCertificationError, TaskAssignmentError) as e:
            raise BadRequest(e)


class TimeEntryViewSet(ModelViewSet):
    serializer_class = TimeEntrySerializer

    def get_queryset(self):
        return TimeEntry.objects.all()


class WorkerViewSet(ModelViewSet):
    serializer_class = WorkerSerializer

    def get_queryset(self):
        return Worker.objects.all()

    @detail_route(methods=['post'])
    def stop_timer(self, request):
        try:
            time_entry = time_tracking.stop_timer(self.get_object())
            return TimeEntrySerializer(time_entry).data
        except TimerError as e:
            raise BadRequest(e)

    @detail_route(methods=['post'])
    def start_timer(self, request):
        try:
            if request.method == 'POST':
                timer = time_tracking.start_timer(
                    self.get_object,
                    assignment_id=request.data.get('assignment'))
                return TaskTimerSerializer(timer).data
        except TaskAssignment.DoesNotExist:
            raise BadRequest('Worker is not assigned to this task id.')
        except TimerError as e:
            raise BadRequest(e)


class WorkerCertificationViewSet(ModelViewSet):
    serializer_class = WorkerCertificationSerializer

    def get_queryset(self):
        return WorkerCertification.objects.all()
