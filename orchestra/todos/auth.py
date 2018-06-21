from rest_framework import permissions

from orchestra.models import Worker
from orchestra.models import Task


class IsAssociatedWithTodosProject(permissions.BasePermission):
    """
    Ensures that a user's worker is accoiated with the todo's project.
    """

    def has_object_permission(self, request, view, todo):
        worker = Worker.objects.get(user=request.user)
        project = todo.task.project
        return (
            worker.is_project_admin() or
            worker.assignments.filter(task__project=project).exists())


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
            task = Task.objects.get(id=task_id) if task_id else None
            return task and \
                worker.assignments.filter(task__project=task.project).exists()
        return False
