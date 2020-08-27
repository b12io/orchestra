from rest_framework import permissions

from orchestra.models import Worker
from orchestra.utils.notifications import message_experts_slack_group


class IsAssociatedWorker(permissions.BasePermission):
    """
    Permission for objects with `worker` field. Checks if request.user matches
    worker on object.
    """

    def has_object_permission(self, request, view, obj):
        worker = Worker.objects.get(user=request.user)
        return obj.worker == worker


def get_todo_change(old_todo, new_todo):
    # When activity_log is updated, `todo_change = None`
    # to avoid triggering any slack messages
    todo_change = None
    if old_todo.completed != new_todo.completed:
        todo_change = 'complete' if new_todo.completed else 'incomplete'
    elif old_todo.skipped_datetime != new_todo.skipped_datetime:
        todo_change = 'not relevant' \
            if new_todo.skipped_datetime else 'relevant'
    return todo_change


def notify_single_todo_update(todo_change, todo, sender):
    # To avoid Slack noise, only send updates for changed TODOs with
    # depth 0 (no parent) or 1 (no grantparent).
    if todo_change and \
            (not (todo.parent_todo and todo.parent_todo.parent_todo)):
        message = '{} has marked `{}` as `{}`.'.format(
            sender,
            todo.title,
            todo_change)
        message_experts_slack_group(
            todo.task.project.slack_group_id, message)
