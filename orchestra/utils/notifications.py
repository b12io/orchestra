from urllib.parse import urljoin

from django.conf import settings
from django.core.mail import send_mail
from django.core.urlresolvers import reverse

from orchestra.models import Task
from orchestra.slack import SlackService
from orchestra.utils.settings import run_if
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import current_assignment


# TODO(jrbotros): design HTML template
def notify_status_change(task, previous_status=None):
    """
    Notify workers after task has changed state
    """
    task_assignments = assignment_history(task)
    current_task_assignment = current_assignment(task)
    current_worker = None
    if current_task_assignment:
        current_worker = current_task_assignment.worker
    message_info = None

    # Notify worker when task initially picked up
    if task.status == Task.Status.PROCESSING:
        message_info = {
            'subject': "You've been assigned to a new task!",
            'message': ("You've been assigned to a new task. We can't wait "
                        "to see the great things you'll do!"),
            'recipient_list': [current_worker.user.email]
        }
    # Notify worker when assignment selected for review
    elif task.status == Task.Status.PENDING_REVIEW:
        message_info = {
            'subject': 'Your task is under review!',
            'message': ('Thanks for all your hard work, {}! The following '
                        'task was randomly selected for review by another '
                        'expert; you should hear back soon!').format(
                            current_worker.user.username),
            'recipient_list': [current_worker.user.email]
        }
    # Notify worker when assignment rejected
    elif task.status == Task.Status.POST_REVIEW_PROCESSING:
        message_info = {
            'subject': 'Your task has been returned',
            'message': ('Your reviewer sent back your task for a bit more '
                        'polish. Check out the feedback as soon as you can!'),
            'recipient_list': [current_worker.user.email]
        }
    # Notify all workers on a task when it has been completed
    elif task.status == Task.Status.COMPLETE:
        message_info = {
            'subject': 'Task complete!',
            'message': 'Congratulations! The task you worked on is complete.',
            'recipient_list': [assignment.worker.user.email
                               for assignment in task_assignments
                               if assignment.worker
                               and assignment.worker.user.email]
        }
    # Notify reviewer when task pending update is ready for re-review, but not
    # for a task moving from PENDING_REVIEW to REVIEWING
    elif (task.status == Task.Status.REVIEWING and
          previous_status == Task.Status.POST_REVIEW_PROCESSING):
            message_info = {
                'subject': 'A task is ready for re-review!',
                'message': ('A task has been updated and is ready for '
                            're-review!'),
                'recipient_list': [current_worker.user.email]
            }

    # Notify all workers on a task when it has been aborted
    elif task.status == Task.Status.ABORTED:
        message_info = {
            'subject': 'A task you were working on has been ended',
            'message': ('Unfortunately, the task you were working on has '
                        'been ended. Please reach out to us if you think this '
                        'has been done in error.'),
            'recipient_list': [assignment.worker.user.email
                               for assignment in task_assignments
                               if assignment.worker
                               and assignment.worker.user.email]
        }

    _notify_internal_slack_status_change(task, current_worker)

    if message_info is not None:
        message_info['message'] += _task_information(task)
        send_mail(from_email=settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL,
                  fail_silently=True,
                  **message_info)


def _task_information(task):
    # TODO(jrbotros): incorporate Django sites framework
    dashboard_link = urljoin(settings.ORCHESTRA_URL,
                             reverse('orchestra:index'))
    task_information = ('\n\n'
                        'Project: {} | {}\n'
                        'Task: {}\n\n'
                        'View dashboard: {}\n').format(
                            task.project.workflow_slug,
                            task.project.short_description,
                            task.step_slug,
                            dashboard_link)

    if task.project.slack_group_id:
        slack_link = urljoin(settings.SLACK_EXPERTS_BASE_URL,
                             task.project.slack_group_id)
        task_information += 'View Slack channel: {}'.format(slack_link)

    return task_information


@run_if('SLACK_INTERNAL')
def _notify_internal_slack_status_change(task, current_worker):
    slack_statuses = {
        Task.Status.PROCESSING: 'Task has been picked up by a worker.',
        Task.Status.PENDING_REVIEW: 'Task is awaiting review.',
        Task.Status.REVIEWING: 'Task is under review.',
        Task.Status.POST_REVIEW_PROCESSING: 'Task was returned by reviewer.',
        Task.Status.COMPLETE: 'Task has been completed.',
        Task.Status.ABORTED: 'Task has been aborted.',
    }

    slack = SlackService(settings.SLACK_INTERNAL_API_KEY)
    slack_message = ('*{}*\n'
                     '>>>'
                     'Current worker: {}'
                     '{}').format(slack_statuses[task.status],
                                  current_worker,
                                  _task_information(task))
    slack.chat.post_message(settings.SLACK_INTERNAL_NOTIFICATION_CHANNEL,
                            slack_message)
