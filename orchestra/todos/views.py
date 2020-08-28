import logging

from rest_framework import generics
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from jsonview.exceptions import BadRequest
from django_filters import rest_framework as filters

from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import TodoQA
from orchestra.models import TodoListTemplate
from orchestra.models import Worker
from orchestra.todos.serializers import BulkTodoSerializer
from orchestra.todos.serializers import BulkTodoSerializerWithQAField
from orchestra.todos.serializers import BulkTodoSerializerWithQASerializer
from orchestra.todos.serializers import TodoQASerializer
from orchestra.todos.serializers import TodoListTemplateSerializer
from orchestra.utils.view_helpers import get_todo_change
from orchestra.utils.view_helpers import notify_todo_created
from orchestra.utils.view_helpers import notify_single_todo_update
from orchestra.todos.api import add_todolist_template
from orchestra.utils.decorators import api_endpoint
from orchestra.todos.auth import IsAssociatedWithTodosProject
from orchestra.todos.auth import IsAssociatedWithProject
from orchestra.todos.auth import IsAssociatedWithTask
from orchestra.project_api.auth import SignedUser

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


class GenericTodoViewset(ModelViewSet):
    serializer_class = BulkTodoSerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filterset_fields = ('project', 'step',)
    queryset = Todo.objects.all()

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True

        return super().get_serializer(*args, **kwargs)

    def get_queryset(self, ids=None):
        queryset = super().get_queryset()
        if ids:
            queryset = queryset.filter(id__in=ids)
        return queryset.order_by('-created_at')

    @action(detail=False, methods=['put'])
    def put(self, request, *args, **kwargs):
        ids = [x['id'] for x in request.data]
        instances = self.get_queryset(ids=ids)
        serializer = self.get_serializer(
            instances, data=request.data, partial=False, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        data = serializer.data
        return Response(data)

    def _get_sender(self):
        if isinstance(self.request.user, SignedUser):
            return None
        return Worker.objects.get(
            user=self.request.user).formatted_slack_username()

    def perform_update(self, serializer):
        if isinstance(serializer.validated_data, list):
            serializer.save()
        else:
            todo = serializer.save()
            old_todo = self.get_object()
            todo_change = get_todo_change(old_todo, todo)
            sender = self._get_sender()
            notify_single_todo_update(
                todo_change, todo, sender=sender)

    def perform_create(self, serializer):
        todo = serializer.save()
        if isinstance(todo, Todo):
            sender = self._get_sender()
            notify_todo_created(todo, sender)


class TodoViewset(GenericTodoViewset):
    def get_permissions(self):
        permission_classes = (permissions.IsAuthenticated,
                              IsAssociatedWithProject)
        if self.action == 'update':
            permission_classes = (permissions.IsAuthenticated,
                                  IsAssociatedWithTodosProject)
        return [permission() for permission in permission_classes]

    def get_serializer_class(self):
        if self.action == 'list' or self.action == 'create':
            # Only include todo QA data for users in the
            # `project_admins` group.
            if self.request.user.groups.filter(
                    name='project_admins').exists():
                return BulkTodoSerializerWithQASerializer
            else:
                return BulkTodoSerializerWithQAField
        else:
            return super().get_serializer_class()
