from orchestra.models import Iteration
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TaskTimer
from orchestra.models import TimeEntry
from orchestra.models import WorkerCertification
from rest_framework import serializers


class ProjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Project

        fields = (
            'id',
            'workflow_slug',
            'workflow_version_slug',
            'short_description',
            'start_datetime',
            'priority',
            'project_data',
            'team_messages_url',
            'task_class',
        )

    workflow_slug = serializers.SerializerMethodField()

    def get_workflow_slug(self, obj):
        return obj.workflow_version.workflow.slug

    workflow_version_slug = serializers.SlugRelatedField(
        source='workflow_version', slug_field='slug', read_only=True)

    task_class = serializers.ChoiceField(
        choices=WorkerCertification.TASK_CLASS_CHOICES)

    project_data = serializers.SerializerMethodField()

    def get_project_data(self, obj):
        """
        This function exists to automatically deserialize the JSON blob from
        the `project_data` JSONField
        """
        return obj.project_data


class TaskSerializer(serializers.ModelSerializer):

    class Meta:
        model = Task

        fields = (
            'id',
            'step_slug',
            'project',
            'status',
            'latest_data',
            'assignments',
            'start_datetime'
        )

    step_slug = serializers.SlugRelatedField(source='step',
                                             slug_field='slug',
                                             read_only=True)

    status = serializers.SerializerMethodField()
    latest_data = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()

    def get_status(self, obj):
        return dict(Task.STATUS_CHOICES).get(obj.status, None)

    def get_latest_data(self, obj):
        """
        Return latest input data for a specified task.

        Args:
            task (orchestra.models.Task):
                The task object for which to retrieve data.

        Returns:
            latest_data (str):
                A serialized JSON blob containing the latest input data.
        """
        active_assignment = (obj.assignments
                             .filter(status=TaskAssignment.Status.PROCESSING))
        if active_assignment.exists():
            assignment = active_assignment[0]
        else:
            assignment = (obj.assignments.all()
                          .order_by('-assignment_counter').first())
        if not assignment:
            return None

        latest_data = assignment.in_progress_task_data
        return latest_data

    def get_assignments(self, obj):
        assignments = TaskAssignmentSerializer(obj.assignments.all()
                                               .order_by('assignment_counter'),
                                               many=True)
        return assignments.data


class TaskAssignmentSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskAssignment

        fields = (
            'id',
            'start_datetime',
            'worker',
            'task',
            'status',
            'in_progress_task_data',
            'iterations',
        )

    worker = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    in_progress_task_data = serializers.SerializerMethodField()
    iterations = serializers.SerializerMethodField()

    def get_worker(self, obj):
        if not obj.worker:
            return {
                'id': None,
                'username': None,
                'first_name': None,
                'last_name': None,
            }
        return {
            'id': obj.worker.id,
            'username': obj.worker.user.username,
            'first_name': obj.worker.user.first_name,
            'last_name': obj.worker.user.last_name,
        }

    def get_status(self, obj):
        return dict(TaskAssignment.STATUS_CHOICES).get(obj.status, None)

    def get_iterations(self, obj):
        iterations = IterationSerializer(
            obj.iterations.order_by('start_datetime'), many=True)
        return iterations.data

    def get_in_progress_task_data(self, obj):
        """
        This function exists to automatically deserialize the JSON blob from
        the `in_progress_task_data` JSONField

        TODO(derek): maybe make a custom JSON serializer field type?
        """
        return obj.in_progress_task_data


class TimeEntrySerializer(serializers.ModelSerializer):

    class Meta:
        model = TimeEntry
        fields = ('id', 'date', 'time_worked', 'description', 'assignment')
        read_only_fields = ('id',)


class TaskTimerSerializer(serializers.ModelSerializer):

    class Meta:
        model = TaskTimer


class IterationSerializer(serializers.ModelSerializer):

    class Meta:
        model = Iteration

        fields = (
            'id',
            'start_datetime',
            'end_datetime',
            'status',
            'assignment',
            'submitted_data',
        )

    status = serializers.SerializerMethodField()
    submitted_data = serializers.SerializerMethodField()

    def get_status(self, obj):
        return dict(Iteration.STATUS_CHOICES).get(obj.status, None)

    def get_submitted_data(self, obj):
        """
        This function exists to automatically deserialize the JSON blob from
        the `in_progress_task_data` JSONField
        """
        return obj.submitted_data
