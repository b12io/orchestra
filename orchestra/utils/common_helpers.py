from rest_framework import permissions

from orchestra.models import Step
from orchestra.models import Worker
from orchestra.project_api.auth import SignedUser
from orchestra.utils.notifications import message_experts_slack_group


class IsAssociatedWorker(permissions.BasePermission):
    """
    Permission for objects with `worker` field. Checks if request.user matches
    worker on object.
    """

    def has_object_permission(self, request, view, obj):
        worker = Worker.objects.get(user=request.user)
        return obj.worker == worker


def get_changed_fields(old_todo, new_todo):
    # To avoid Slack noise, only care about title and details
    changed_fields = []
    if old_todo.title != new_todo.title:
        changed_fields.append('title')
    if old_todo.details != new_todo.details:
        changed_fields.append('details')
    if len(changed_fields) > 1:
        changed_fields[-1] = 'and {}'.format(changed_fields[-1])
    return ' '.join(changed_fields)


def get_relevance_and_completion_changes(old_todo, new_todo):
    # When activity_log is updated, `todo_change = ''`
    # to avoid triggering any slack messages
    todo_change = ''
    if old_todo.completed != new_todo.completed:
        todo_change = 'complete' if new_todo.completed else 'incomplete'
    elif old_todo.skipped_datetime != new_todo.skipped_datetime:
        todo_change = 'not relevant' \
            if new_todo.skipped_datetime else 'relevant'
    return todo_change


def get_update_message(old_todo, new_todo, sender=None):
    message = ''
    changes = get_relevance_and_completion_changes(old_todo, new_todo)
    changed_fields = get_changed_fields(old_todo, new_todo)
    head = '{} has updated `{}`:'.format(sender, new_todo.title) \
        if sender else '`{}` has been updated:'.format(new_todo.title)
    body = 'marked {}'.format(changes) if changes else ''
    tail = 'changed {}'.format(changed_fields) if changed_fields else ''
    if body or tail:
        tail = ', {}'.format(tail) if body and tail else '{}'.format(tail)
        message = '{} {}{}'.format(head, body, tail)
    return message


def _get_sender(user):
    if isinstance(user, SignedUser):
        return None
    return Worker.objects.get(
        user=user).formatted_slack_username()


def notify_single_todo_update(user, old_todo, todo):
    # To avoid Slack noise, only send updates for changed TODOs with
    # depth 0 (no parent) or 1 (no grandparent).
    sender = _get_sender(user)
    message = get_update_message(old_todo, todo, sender)
    if message and \
            (not (todo.parent_todo and todo.parent_todo.parent_todo)):
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


def get_step_by_project_id_and_step_slug(project_id, step_slug):
    step = Step.objects.get(
        slug=step_slug,
        workflow_version__projects__id=project_id)
    return step
