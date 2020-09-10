from rest_framework import permissions

from orchestra.models import Worker
from orchestra.models import Task
from orchestra.models import Todo
from orchestra.models import TodoQA


class IsAssociatedWithTodosProject(permissions.BasePermission):
    """
    Ensures that a user's worker is accoiated with the todo's project.
    """

    def has_object_permission(self, request, view, obj):
        worker = Worker.objects.get(user=request.user)
        if isinstance(obj, Todo):
            project = obj.project
        elif isinstance(obj, TodoQA):
            project = obj.todo.project
        else:
            project = None
        return (
            project and
            (worker.is_project_admin() or
             worker.assignments.filter(task__project=project).exists()))


class IsAssociatedWithProject(permissions.BasePermission):
    """
    Ensures that a user's worker is associated with the request's
    `project`.

    """

    def has_permission(self, request, view):
        worker = Worker.objects.get(user=request.user)
        todo_id = request.data.get('todo')
        if todo_id is not None:
            project_id = Todo.objects.get(id=todo_id).project_id
        if project_id is None:
            project_id = request.query_params.get('project')
        if worker.is_project_admin():
            return True
        return worker.assignments.filter(task__project__id=project_id).exists()


class IsAssociatedWithTask(permissions.BasePermission):
    """
    Ensures that a user's worker is associated with the request's
    `task`.

    """

    def has_permission(self, request, view):
        worker = Worker.objects.get(user=request.user)
        if worker.is_project_admin():
            return True
        if request.method == 'GET':
            task_id = request.query_params.get('task')
            return worker.assignments.filter(task=task_id).exists()
        return False
