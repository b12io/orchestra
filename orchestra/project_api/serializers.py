from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import WorkerCertification
from orchestra.utils.task_lifecycle import _get_latest_task_data
from rest_framework import serializers


class ProjectSerializer(serializers.ModelSerializer):

    class Meta:
        model = Project

        fields = (
            'id',
            'workflow_slug',
            'short_description',
            'start_datetime',
            'priority',
            'project_data',
            'review_document_url',
            'task_class',
        )

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
        )

    status = serializers.SerializerMethodField()
    latest_data = serializers.SerializerMethodField()
    assignments = serializers.SerializerMethodField()

    def get_status(self, obj):
        return dict(Task.STATUS_CHOICES).get(obj.status, None)

    def get_latest_data(self, obj):
        return _get_latest_task_data(obj)

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
            'snapshots',
        )

    worker = serializers.StringRelatedField()
    status = serializers.SerializerMethodField()
    in_progress_task_data = serializers.SerializerMethodField()
    snapshots = serializers.SerializerMethodField()

    def get_status(self, obj):
        return dict(TaskAssignment.STATUS_CHOICES).get(obj.status, None)

    def get_snapshots(self, obj):
        """
        This function exists to automatically deserialize the JSON blob from
        the `snapshots` JSONField
        """
        return obj.snapshots

    def get_in_progress_task_data(self, obj):
        """
        This function exists to automatically deserialize the JSON blob from
        the `in_progress_task_data` JSONField

        TODO(derek): maybe make a custom JSON serializer field type?
        """
        return obj.in_progress_task_data
