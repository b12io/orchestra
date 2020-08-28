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
    # TODO(murat): think about updates we want to notify about
    # When activity_log is updated, `todo_change = None`
    # to avoid triggering any slack messages
    changed_fields = []
    todo_change = ''
    if old_todo.completed != new_todo.completed:
        todo_change = 'complete' if new_todo.completed else 'incomplete'
    elif old_todo.skipped_datetime != new_todo.skipped_datetime:
        todo_change = 'not relevant' \
            if new_todo.skipped_datetime else 'relevant'
    if old_todo.title != new_todo.title:
        changed_fields.append('title')
    if old_todo.details != new_todo.details:
        changed_fields.append('details')
    if old_todo.section != new_todo.section:
        changed_fields.append('section')
    if old_todo.order != old_todo.order:
        changed_fields.append('order')
    if old_todo.status != old_todo.status:
        changed_fields.append('status')
    dict1 = new_todo.additional_data
    dict2 = old_todo.additional_data
    changed_subfields = [k for k in dict1 if dict1.get(k) != dict2.get(k)]
    changed_fields.extend(changed_subfields)
    if len(todo_change):
        return '{}. Changed fields: {}'.format(
            todo_change, ', '.join(changed_fields))
    return 'changed. Changed fields: {}'.format(', '.join(changed_fields))


def notify_single_todo_update(todo_change, todo, sender):
    # To avoid Slack noise, only send updates for changed TODOs with
    # depth 0 (no parent) or 1 (no grandparent).
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


def notify_todo_created(todo, sender):
    tasks = (
        task for task in todo.project.tasks.all()
        if task.step.slug == todo.step.slug)
    recipients = ' & '.join(
        assignment.worker.formatted_slack_username()
        for task in tasks
        for assignment in task.assignments.all()
        if assignment and assignment.worker)
    message = '{} has created a new todo `{}` for {}.'.format(
        sender,
        todo.title,
        recipients if recipients else '`{}`'.format(todo.step.slug))
    message_experts_slack_group(
        todo.project.slack_group_id, message)
