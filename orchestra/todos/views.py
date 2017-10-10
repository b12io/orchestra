from rest_framework import generics
from rest_framework import permissions

from orchestra.models import Todo
from orchestra.models import Worker
from orchestra.todos.serializers import TodoSerializer
from orchestra.utils.notifications import message_experts_slack_group


class TodoList(generics.ListCreateAPIView):
    # TODO(marcua): Add orchestra.utils.view_helpers.IsAssociatedProject
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = TodoSerializer
    queryset = Todo.objects.all()
    # filter_backends = (filters.DjangoFilterBackend,)
    # filter_class = TimeEntryFilter

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
    # TODO(marcua): Add orchestra.utils.view_helpers.IsAssociatedProject
    permission_classes = (permissions.IsAuthenticated,)
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
