import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import redirect
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from rest_framework import generics
from rest_framework import permissions
from rest_framework.viewsets import ModelViewSet
from rest_framework.response import Response
from rest_framework.decorators import action
from jsonview.exceptions import BadRequest

from orchestra.core.errors import TodoListTemplateValidationError
from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import TodoQA
from orchestra.models import TodoListTemplate
from orchestra.todos.forms import ImportTodoListTemplateFromSpreadsheetForm
from orchestra.todos.filters import QueryParamsFilterBackend
from orchestra.todos.serializers import BulkTodoSerializer
from orchestra.todos.serializers import BulkTodoSerializerWithoutQA
from orchestra.todos.serializers import BulkTodoSerializerWithQA
from orchestra.todos.serializers import TodoQASerializer
from orchestra.todos.serializers import TodoListTemplateSerializer
from orchestra.utils.common_helpers import notify_todo_created
from orchestra.utils.common_helpers import notify_single_todo_update
from orchestra.todos.api import add_todolist_template
from orchestra.utils.decorators import api_endpoint
from orchestra.todos.auth import IsAssociatedWithTodosProject
from orchestra.todos.auth import IsAssociatedWithProject
from orchestra.todos.auth import IsAssociatedWithTask
from orchestra.todos.import_export import import_from_spreadsheet

logger = logging.getLogger(__name__)


@api_endpoint(methods=['POST'],
              permissions=(IsAssociatedWithProject,),
              logger=logger)
def update_todos_from_todolist_template(request):
    todolist_template_slug = request.data.get('todolist_template')
    project_id = request.data.get('project')
    step_slug = request.data.get('step')
    try:
        add_todolist_template(todolist_template_slug, project_id, step_slug)
        todos = Todo.objects.filter(
            project__id=project_id,
            step__slug=step_slug).order_by('-created_at')
        serializer = BulkTodoSerializerWithoutQA(todos, many=True)
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
    task_todo_qas = TodoQA.objects.filter(todo__project__tasks__id=task_id)

    if task_todo_qas.exists():
        todo_qas = task_todo_qas
    else:
        task = Task.objects.get(pk=task_id)
        most_recent_worker_task_todo_qa = TodoQA.objects.filter(
            todo__project__tasks__assignments__worker__user=request.user,
            todo__step__slug=task.step.slug
        ).order_by('-created_at').first()

        if most_recent_worker_task_todo_qa:
            project = most_recent_worker_task_todo_qa.todo.project
            step = most_recent_worker_task_todo_qa.todo.step
            todo_qas = TodoQA.objects.filter(
                todo__project=project,
                todo__step=step,
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
    """
    A base viewset inherited by multiple viewsets, created
    to de-duplicate Todo-related views.
    It lacks permission and auth classes, so that child
    classes can select their own.
    """
    serializer_class = BulkTodoSerializer
    filter_backends = (QueryParamsFilterBackend,)
    # Note: additional_data__nested_field is not supported in filterset_fields
    # This issue can be fixed when we migrate to Django 3.1
    # and convert additional_data from django-jsonfields to the native one.
    filterset_fields = ('project__id', 'step__slug', 'id__in')
    queryset = Todo.objects.select_related('step', 'qa').all()

    def get_serializer(self, *args, **kwargs):
        if isinstance(kwargs.get('data', {}), list):
            kwargs['many'] = True

        return super().get_serializer(*args, **kwargs)

    def get_queryset(self, ids=None):
        queryset = super().get_queryset()
        if ids:
            queryset = queryset.filter(id__in=ids)
        return queryset.order_by('-created_at')

    @action(detail=False, methods=['delete'])
    def delete(self, request, *args, **kwargs):
        data = self.get_queryset(ids=request.data).delete()
        return Response(data)

    @action(detail=False, methods=['put'])
    def put(self, request, *args, **kwargs):
        partial = kwargs.get('partial', False)
        ids = [x['id'] for x in request.data]
        # Sort the queryset and data by primary key
        # so we update the correct records.
        sorted_data = sorted(request.data, key=lambda x: x['id'])
        instances = self.get_queryset(ids=ids).order_by('id')
        serializer = self.get_serializer(
            instances, data=sorted_data, partial=partial, many=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        data = serializer.data
        return Response(data)

    @action(detail=False, methods=['patch'])
    def patch(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.put(request, *args, **kwargs)

    def perform_update(self, serializer):
        todo = serializer.save()
        if isinstance(todo, Todo):
            old_todo = self.get_object()
            notify_single_todo_update(
                self.request.user, old_todo, todo)

    def perform_create(self, serializer):
        todo = serializer.save()
        if isinstance(todo, Todo):
            notify_todo_created(todo, self.request.user)


class TodoViewset(GenericTodoViewset):
    """
    This viewset inherits from GenericTodoViewset is used by two endpoints
    (see urls.py).
    todo/ -- For creating and listing Todos.
    todo/1234/ -- For updating a Todo.
    """
    http_method_names = ['get', 'post', 'put', 'delete']

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
                return BulkTodoSerializerWithQA
            else:
                return BulkTodoSerializerWithoutQA
        else:
            return super().get_serializer_class()


@method_decorator(staff_member_required, name='dispatch')
class ImportTodoListTemplateFromSpreadsheet(View):
    TEMPLATE = 'orchestra/import_todo_list_template_from_spreadsheet.html'

    def get(self, request, pk):
        # Display a form with a spreadsheet URL for import.
        return render(
            request,
            self.TEMPLATE,
            {'form': ImportTodoListTemplateFromSpreadsheetForm(initial={})})

    def post(self, request, pk):
        # Try to import the spreadsheet and redirect back to the admin
        # entry for the imported TodoListTemplate. If we encounter an
        # error, display the error on the form.
        form = ImportTodoListTemplateFromSpreadsheetForm(request.POST)
        context = {'form': form}
        if form.is_valid():
            try:
                todo_list_template = TodoListTemplate.objects.get(
                    id=pk)
                import_from_spreadsheet(
                    todo_list_template,
                    form.cleaned_data['spreadsheet_url'],
                    request)
                messages.info(
                    request, 'Successfully imported from spreadsheet.')
                return redirect(
                    'admin:orchestra_todolisttemplate_change',
                    pk)
            except TodoListTemplateValidationError as e:
                context['import_error'] = str(e)
        else:
            context['import_error'] = 'Please provide a spreadsheet URL'
        return render(
            request,
            self.TEMPLATE,
            context)
