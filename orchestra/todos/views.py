from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response

from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import TodoListTemplate
from orchestra.models import Worker
from orchestra.todos.serializers import TodoSerializer
from orchestra.todos.serializers import TodoListTemplateSerializer
from orchestra.utils.notifications import message_experts_slack_group
from orchestra.todos.api import add_todolist_template
from orchestra.todos.decorators import api_endpoint
from orchestra.todos.auth import IsAssociatedWithTodosProject
from orchestra.todos.auth import IsAssociatedWithProject


@api_endpoint(['POST'])
def add_todos_from_todolist_template(request):
    todolist_template_id = request.data.get('todolist_template')
    task_id = request.data.get('task')
    add_todolist_template(todolist_template_id, task_id)
    project = Task.objects.get(id=task_id).project
    todos = Todo.objects.filter(
        task__project__id=int(project.id)).order_by('-created_at')
    serializer = TodoSerializer(todos, many=True)
    return Response(serializer.data)


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


class TodoListTemplateDetail(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    serializer_class = TodoListTemplateSerializer
    queryset = TodoListTemplate.objects.all()


class TodoListTemplateList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    serializer_class = TodoListTemplateSerializer
    queryset = TodoListTemplate.objects.all()
