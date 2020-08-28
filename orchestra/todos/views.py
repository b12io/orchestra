import logging

from rest_framework import generics
from rest_framework import permissions
from rest_framework.response import Response
from jsonview.exceptions import BadRequest

from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import TodoQA
from orchestra.models import TodoListTemplate
from orchestra.models import Worker
from orchestra.todos.serializers import BulkTodoSerializerWithQAField
from orchestra.todos.serializers import BulkTodoSerializerWithQASerializer
from orchestra.todos.serializers import TodoQASerializer
from orchestra.todos.serializers import TodoListTemplateSerializer
from orchestra.utils.view_helpers import get_todo_change
from orchestra.utils.view_helpers import notify_single_todo_update
from orchestra.utils.notifications import message_experts_slack_group
from orchestra.todos.api import add_todolist_template
from orchestra.utils.decorators import api_endpoint
from orchestra.todos.auth import IsAssociatedWithTodosProject
from orchestra.todos.auth import IsAssociatedWithProject
from orchestra.todos.auth import IsAssociatedWithTask

logger = logging.getLogger(__name__)


def _set_data(obj, key, value):
    obj[key] = value
    return obj


@api_endpoint(methods=['POST'],
              permissions=(IsAssociatedWithProject,),
              logger=logger)
def update_todos_from_todolist_template(request):
    todolist_template_slug = request.data.get('todolist_template')
    task_id = request.data.get('task')
    try:
        add_todolist_template(todolist_template_slug, task_id)
        project = Task.objects.get(id=task_id).project
        todos = Todo.objects.filter(
            task__project__id=int(project.id)).order_by('-created_at')
        serializer = BulkTodoSerializerWithQAField(todos, many=True)
        return Response(serializer.data)
    except TodoListTemplate.DoesNotExist:
        raise BadRequest('TodoList Template not found for the given slug.')


@api_endpoint(methods=['GET'],
              permissions=(permissions.IsAuthenticated,
                           IsAssociatedWithTask),
              logger=logger)
def worker_task_recent_todo_qas(request):
    """
    Returns TodoQA recommendations for the requesting user and task.

    The TodoQAs for the recommendation are selected using the following logic:
    1. If the given task has TodoQAs, use them.
    2. Otherwise, use the TodoQAs from the requesting user's most recent
    task with matching task slug.
    """
    task_id = request.query_params.get('task')
    task_todo_qas = TodoQA.objects.filter(todo__task=task_id)

    if task_todo_qas.exists():
        todo_qas = task_todo_qas
    else:
        task = Task.objects.get(pk=task_id)
        most_recent_worker_task_todo_qa = TodoQA.objects.filter(
            todo__task__assignments__worker__user=request.user,
            todo__task__step__slug=task.step.slug
        ).order_by('-created_at').first()

        if most_recent_worker_task_todo_qa:
            todo_qas = TodoQA.objects.filter(
                todo__task=most_recent_worker_task_todo_qa.todo.task,
                approved=False)
        else:
            todo_qas = TodoQA.objects.none()

    todos_recommendation = {todo_qa.todo.title: TodoQASerializer(
        todo_qa).data for todo_qa in todo_qas}
    return Response(todos_recommendation)


class TodoList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,
                          IsAssociatedWithProject)

    queryset = Todo.objects.all()

    def get_serializer_class(self):
        # Only include todo QA data for users in the `project_admins` group.
        if self.request.user.groups.filter(
                name='project_admins').exists():
            return BulkTodoSerializerWithQASerializer
        else:
            return BulkTodoSerializerWithQAField

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
        notify_todo_created(todo, sender)


class TodoDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated,
                          IsAssociatedWithTodosProject)
    queryset = Todo.objects.all()
    serializer_class = BulkTodoSerializerWithQAField

    def perform_update(self, serializer):
        old_todo = self.get_object()
        todo = serializer.save()
        sender = Worker.objects.get(
            user=self.request.user).formatted_slack_username()
        todo_change = get_todo_change(old_todo, todo)
        notify_single_todo_update(todo_change, todo, sender)


class TodoQADetail(generics.UpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,
                          IsAssociatedWithTodosProject)

    serializer_class = TodoQASerializer
    queryset = TodoQA.objects.all()


class TodoQAList(generics.CreateAPIView):
    permission_classes = (permissions.IsAuthenticated,
                          IsAssociatedWithProject)

    serializer_class = TodoQASerializer
    queryset = TodoQA.objects.all()


class TodoListTemplateDetail(generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    serializer_class = TodoListTemplateSerializer
    queryset = TodoListTemplate.objects.all()


class TodoListTemplateList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)

    serializer_class = TodoListTemplateSerializer
    queryset = TodoListTemplate.objects.all()
