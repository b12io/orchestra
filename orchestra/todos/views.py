import json

from rest_framework import generics
from rest_framework import permissions

from orchestra.models import Todo
from orchestra.models import Worker
from orchestra.todos.serializers import TodoSerializer
from orchestra.utils.notifications import message_experts_slack_group


class IsAssociatedWithTodosProject(permissions.BasePermission):
    """
    Ensures that a user's worker is accoiated with the todo's project.
    """

    def has_object_permission(self, request, view, todo):
        worker = Worker.objects.get(user=request.user)
        project = todo.task.project
        return worker.assignments.filter(task__project=project).exists()


class IsAssociatedWithProject(permissions.BasePermission):
    """
    Ensures that a user's worker is associated with the request's
    `project`.

    """

    def has_permission(self, request, view):
        worker = Worker.objects.get(user=request.user)
        if request.method == 'GET':
            # List calls have a project ID
            project_id = request.query_params.get('project')
            return worker.assignments.filter(task__project=project_id).exists()
        elif request.method == 'POST':
            # Create calls have a task ID
            task_id = request.data.get('task')
            return worker.assignments.filter(task=task_id).exists()
        return False


class TodoList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,
                          IsAssociatedWithProject)

    serializer_class = TodoSerializer
    queryset = Todo.objects.all()

    def get_queryset(self):
        queryset = Todo.objects.all()
        project_id = self.request.query_params.get('project', None)
        if project_id is not None:
            queryset = queryset.filter(task__project__id=int(project_id))
        queryset = queryset.order_by('-created_at')
        return queryset

    def perform_create(self, serializer):
        todo = serializer.save()
        sender = Worker.objects.get(
            user=self.request.user).formatted_slack_username()
        recipients = ' & '.join(
            assignment.worker.formatted_slack_username()
            for assignment in todo.task.assignments.all()
            if assignment and assignment.worker)
        message = '{} has created a new todo `{}` for {}.'.format(
            sender,
            todo.description,
            recipients if recipients else '`{}`'.format(todo.task.step.slug))
        message_experts_slack_group(
            todo.task.project.slack_group_id, message)


class TodoDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,
                          IsAssociatedWithTodosProject)
    queryset = Todo.objects.all()
    serializer_class = TodoSerializer

    def perform_update(self, serializer):
        todo = serializer.save()
        sender = Worker.objects.get(
            user=self.request.user).formatted_slack_username()
        message = '{} has marked `{}` as `{}`.'.format(
            sender,
            todo.description,
            'complete' if todo.completed else 'incomplete')
        message_experts_slack_group(
            todo.task.project.slack_group_id, message)
