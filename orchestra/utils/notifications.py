from urllib.parse import urljoin

from django.conf import settings
from django.urls import reverse

from orchestra.communication.mail import send_mail
from orchestra.communication.slack import OrchestraSlackService
from orchestra.models import CommunicationPreference
from orchestra.models import StaffingRequestInquiry
from orchestra.models import Task
from orchestra.models import Project
from orchestra.utils.decorators import run_if
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import current_assignment


# TODO(jrbotros): design HTML template
def notify_status_change(
        task, previous_status=None, staffing_request_inquiry=None):
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

    _notify_internal_slack_status_change(
        task, current_worker,
        staffing_request_inquiry=staffing_request_inquiry)
    if task.project.slack_group_id:
        _notify_experts_slack_status_change(
            task, current_worker,
            staffing_request_inquiry=staffing_request_inquiry)

    if message_info is not None:
        message_info['message'] += _task_information(task)
        comm_type = (CommunicationPreference.CommunicationType
                     .TASK_STATUS_CHANGE.value)
        send_mail(from_email=settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL,
                  communication_type=comm_type,
                  fail_silently=True,
                  **message_info)


def notify_project_status_change(project):
    extra_explanation = ''
    if project.status == Project.Status.PAUSED:
        status_text = 'paused'
        extra_explanation = (
            'All activities will be put on hold until '
            'the project is reactivated.')
    elif project.status == Project.Status.ACTIVE:
        status_text = 'reactivated'
    elif project.status == Project.Status.COMPLETED:
        status_text = 'completed'
    elif project.status == Project.Status.ABORTED:
        status_text = 'aborted'
    else:
        return
    slack_message = (
        '*Project {} | {} has been {}.*\n'
        '{}'
        ).format(
            project.workflow_version.slug,
            project.short_description,
            status_text,
            extra_explanation)
    message_internal_slack_group(
        settings.SLACK_INTERNAL_NOTIFICATION_CHANNEL, slack_message)
    if project.slack_group_id:
        message_experts_slack_group(project.slack_group_id, slack_message)


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
                                with_user_mention=False,
                                staffing_request_inquiry=None):
    slack = OrchestraSlackService(slack_api_key)
    auto_staff_method = (
        StaffingRequestInquiry.CommunicationMethod.PREVIOUSLY_OPTED_IN)
    is_auto_staffed = (staffing_request_inquiry
                       and staffing_request_inquiry.communication_method
                       == auto_staff_method.value)
    processing_status_message = (
        'Task has been auto-staffed to a worker.'
        if is_auto_staffed else
        'Task has been picked up by a worker.')
    slack_statuses = {
        Task.Status.PROCESSING: processing_status_message,
        Task.Status.PENDING_REVIEW: 'Task is awaiting review.',
        Task.Status.REVIEWING: 'Task is under review.',
        Task.Status.POST_REVIEW_PROCESSING: 'Task was returned by reviewer.',
        Task.Status.COMPLETE: 'Task has been completed.',
        Task.Status.ABORTED: 'Task has been aborted.',
    }
    worker_string = current_worker.user.username if current_worker else None
    slack_user_id = current_worker.slack_user_id if current_worker else None
    if slack_user_id and with_user_mention:
        worker_string += ' (<@{}>)'.format(slack_user_id)
    slack_message = ('*{}*\n'
                     '>>>'
                     'Current worker: {}'
                     '{}').format(slack_statuses[task.status],
                                  worker_string,
                                  _task_information(
                                      task, with_slack_link=with_slack_link))
    slack.chat.post_message(slack_channel, slack_message)


@run_if('ORCHESTRA_SLACK_INTERNAL_ENABLED')
def _notify_internal_slack_status_change(
        task, current_worker, staffing_request_inquiry=None):
    _notify_slack_status_change(
        task, current_worker,
        settings.SLACK_INTERNAL_API_KEY,
        settings.SLACK_INTERNAL_NOTIFICATION_CHANNEL,
        staffing_request_inquiry=staffing_request_inquiry)


@run_if('ORCHESTRA_SLACK_EXPERTS_ENABLED')
def _notify_experts_slack_status_change(
        task, current_worker, staffing_request_inquiry=None):
    _notify_slack_status_change(
        task, current_worker,
        settings.SLACK_EXPERTS_API_KEY,
        task.project.slack_group_id,
        with_slack_link=False,
        with_user_mention=True,
        staffing_request_inquiry=staffing_request_inquiry)


@run_if('ORCHESTRA_SLACK_EXPERTS_ENABLED')
def message_experts_slack_group(slack_channel, slack_message):
    slack = OrchestraSlackService(settings.SLACK_EXPERTS_API_KEY)
    slack.chat.post_message(slack_channel, slack_message)


@run_if('ORCHESTRA_SLACK_INTERNAL_ENABLED')
def message_internal_slack_group(slack_channel, slack_message):
    slack = OrchestraSlackService(settings.SLACK_INTERNAL_API_KEY)
    slack.chat.post_message(slack_channel, slack_message)
