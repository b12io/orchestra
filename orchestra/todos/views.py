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
from orchestra.todos.serializers import TodoSerializer
from orchestra.todos.serializers import TodoWithQASerializer
from orchestra.todos.serializers import TodoQASerializer
from orchestra.todos.serializers import TodoListTemplateSerializer
from orchestra.utils.notifications import message_experts_slack_group
from orchestra.todos.api import add_todolist_template
from orchestra.utils.decorators import api_endpoint
from orchestra.todos.auth import IsAssociatedWithTodosProject
from orchestra.todos.auth import IsAssociatedWithProject
from orchestra.todos.auth import IsAssociatedWithTask

logger = logging.getLogger(__name__)


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
        serializer = TodoSerializer(todos, many=True)
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

    todos_recommendation = {todo_qa.todo.description: TodoQASerializer(
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
            return TodoWithQASerializer
        else:
            return TodoSerializer

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
        old_todo = self.get_object()
        todo = serializer.save()
        sender = Worker.objects.get(
            user=self.request.user).formatted_slack_username()

        if old_todo.completed != todo.completed:
            todo_change = 'complete' if todo.completed else 'incomplete'
        elif old_todo.skipped_datetime != todo.skipped_datetime:
            todo_change = 'not relevant' \
                if todo.skipped_datetime else 'relevant'
        else:
            # When activity_log is updated, `todo_change = None`
            # to avoid triggering any slack messages
            todo_change = None

        # To avoid Slack noise, only send updates for changed TODOs with
        # depth 0 (no parent) or 1 (no grantparent).
        if todo_change and \
                (not (todo.parent_todo and todo.parent_todo.parent_todo)):
            message = '{} has marked `{}` as `{}`.'.format(
                sender,
                todo.description,
                todo_change)
            message_experts_slack_group(
                todo.task.project.slack_group_id, message)


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
