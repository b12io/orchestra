from urllib.parse import urljoin

from django.conf import settings
from django.core.urlresolvers import reverse

from orchestra.models import Task
from orchestra.models import CommunicationPreference
from orchestra.communication.slack import OrchestraSlackService
from orchestra.communication.mail import send_mail
from orchestra.utils.decorators import run_if
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
                               if assignment.worker and
                               assignment.worker.user.email]
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
                               if assignment.worker and
                               assignment.worker.user.email]
        }

    _notify_internal_slack_status_change(task, current_worker)
    if task.project.slack_group_id:
        _notify_experts_slack_status_change(task, current_worker)

    if message_info is not None:
        message_info['message'] += _task_information(task)
        comm_type = (CommunicationPreference.CommunicationType
                     .TASK_STATUS_CHANGE.value)
        send_mail(from_email=settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL,
                  communication_type=comm_type,
                  fail_silently=True,
                  **message_info)


def _task_information(task, with_slack_link=True):
    # TODO(jrbotros): incorporate Django sites framework
    dashboard_link = urljoin(settings.ORCHESTRA_URL,
                             reverse('orchestra:index'))
    task_information = ('\n\n'
                        'Project: {} | {}\n'
                        'Task: {} {}\n\n'
                        'View dashboard: {}\n').format(
                            task.project.workflow_version.slug,
                            task.project.short_description,
                            task.step.slug,
                            task.id,
                            dashboard_link)

    if task.project.slack_group_id and with_slack_link:
        slack_link = urljoin(settings.SLACK_EXPERTS_BASE_URL,
                             task.project.slack_group_id)
        task_information += 'View Slack channel: {}'.format(slack_link)

    return task_information


def _notify_slack_status_change(task, current_worker, slack_api_key,
                                slack_channel, with_slack_link=True,
                                with_user_mention=False):
    slack = OrchestraSlackService(slack_api_key)
    slack_statuses = {
        Task.Status.PROCESSING: 'Task has been picked up by a worker.',
        Task.Status.PENDING_REVIEW: 'Task is awaiting review.',
        Task.Status.REVIEWING: 'Task is under review.',
        Task.Status.POST_REVIEW_PROCESSING: 'Task was returned by reviewer.',
        Task.Status.COMPLETE: 'Task has been completed.',
        Task.Status.ABORTED: 'Task has been aborted.',
    }
    slack_username = getattr(current_worker, 'slack_username', None)
    worker_string = current_worker.user.username if current_worker else None
    if current_worker and slack_username and with_user_mention:
        user_id = slack.users.get_user_id(slack_username)
        worker_string += ' (<@{}|{}>)'.format(user_id, slack_username)
    slack_message = ('*{}*\n'
                     '>>>'
                     'Current worker: {}'
                     '{}').format(slack_statuses[task.status],
                                  worker_string,
                                  _task_information(
                                      task, with_slack_link=with_slack_link))
    slack.chat.post_message(slack_channel, slack_message)


@run_if('ORCHESTRA_SLACK_INTERNAL_ENABLED')
def _notify_internal_slack_status_change(task, current_worker):
    _notify_slack_status_change(task, current_worker,
                                settings.SLACK_INTERNAL_API_KEY,
                                settings.SLACK_INTERNAL_NOTIFICATION_CHANNEL)


@run_if('ORCHESTRA_SLACK_EXPERTS_ENABLED')
def _notify_experts_slack_status_change(task, current_worker):
    _notify_slack_status_change(task, current_worker,
                                settings.SLACK_EXPERTS_API_KEY,
                                task.project.slack_group_id,
                                with_slack_link=False,
                                with_user_mention=True)


@run_if('ORCHESTRA_SLACK_EXPERTS_ENABLED')
def message_experts_slack_group(slack_channel, slack_message):
    slack = OrchestraSlackService(settings.SLACK_EXPERTS_API_KEY)
    slack.chat.post_message(slack_channel, slack_message)
