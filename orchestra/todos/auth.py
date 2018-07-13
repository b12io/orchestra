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
            project = obj.task.project
        elif isinstance(obj, TodoQA):
            project = obj.todo.task.project
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
        if worker.is_project_admin():
            return True
        if request.method == 'GET':
            # List calls have a project ID
            project_id = request.query_params.get('project')
            return worker.assignments.filter(task__project=project_id).exists()
        elif request.method == 'POST':
            # Create calls have a task ID
            task_id = request.data.get('task')
            todo_id = request.data.get('todo')
            try:
                if task_id:
                    task = Task.objects.get(id=task_id)
                elif todo_id:
                    task = Todo.objects.get(id=todo_id).task
                else:
                    task = None
                return task and \
                    worker.assignments.filter(
                        task__project=task.project).exists()
            except (Task.DoesNotExist, Todo.DoesNotExist):
                return False
        return False


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
