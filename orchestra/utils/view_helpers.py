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


def _get_changed_fields(old_todo, new_todo):
    changed_fields = []
    if old_todo.title != new_todo.title:
        changed_fields.append('title')
    if old_todo.details != new_todo.details:
        changed_fields.append('details')
    dict1 = {}
    dict2 = {}
    if isinstance(old_todo.additional_data, dict):
        dict1 = old_todo.additional_data
    if isinstance(new_todo.additional_data, dict):
        dict2 = new_todo.additional_data
    changed_subfields = [k for k in dict1.keys()
                         if dict1.get(k) != dict2.get(k)]
    changed_fields.extend(changed_subfields)
    return changed_fields


def get_todo_change(old_todo, new_todo):
    # When activity_log is updated, `todo_change = None`
    # to avoid triggering any slack messages
    todo_change = ''
    changed_fields = _get_changed_fields(old_todo, new_todo)
    if old_todo.completed != new_todo.completed:
        todo_change = 'complete' if new_todo.completed else 'incomplete'
    elif old_todo.skipped_datetime != new_todo.skipped_datetime:
        todo_change = 'not relevant' \
            if new_todo.skipped_datetime else 'relevant'
    message = ''
    if len(todo_change) and len(changed_fields):
        message = '{}. Changed fields: {}'.format(
            todo_change, ', '.join(changed_fields))
    elif len(changed_fields):
        message = 'changed. Changed fields: {}'.format(
            ', '.join(changed_fields))
    else:
        message = todo_change
    return message


def _get_sender(user):
    if isinstance(user, SignedUser):
        return None
    return Worker.objects.get(
        user=user).formatted_slack_username()


def notify_single_todo_update(user, old_todo, todo):
    # To avoid Slack noise, only send updates for changed TODOs with
    # depth 0 (no parent) or 1 (no grandparent).
    todo_change = get_todo_change(old_todo, todo)
    sender = _get_sender(user)
    if todo_change and \
            (not (todo.parent_todo and todo.parent_todo.parent_todo)):
        if sender:
            message = '{} has marked `{}` as `{}`.'.format(
                sender,
                todo.title,
                todo_change)
        else:
            message = '`{}` was marked as `{}`.'.format(
                todo.title,
                todo_change)
        message_experts_slack_group(
            todo.project.slack_group_id, message)


def notify_todo_created(todo, user):
    sender = _get_sender(user)
    tasks = (
        task for task in todo.project.tasks.all()
        if task.step.slug == todo.step.slug)
    recipients = ' & '.join(
        assignment.worker.formatted_slack_username()
        for task in tasks
        for assignment in task.assignments.all()
        if assignment and assignment.worker)
    if sender:
        message = '{} has created a new todo `{}` for {}.'.format(
            sender,
            todo.title,
            recipients if recipients else '`{}`'.format(todo.step.slug))
    else:
        message = 'A new todo `{}` was created for {}.'.format(
            todo.title,
            recipients if recipients else '`{}`'.format(todo.step.slug))
    message_experts_slack_group(
        todo.project.slack_group_id, message)
