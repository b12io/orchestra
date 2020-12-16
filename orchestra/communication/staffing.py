from annoying.functions import get_object_or_None
from collections import defaultdict
from django.conf import settings
from django.urls import reverse
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from markdown2 import markdown

from orchestra.bots.errors import StaffingResponseException
from orchestra.bots.staffbot import StaffBot
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import TaskStatusError
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse
from orchestra.models import Task
from orchestra.models import Project
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.utils.notifications import message_experts_slack_group
from orchestra.utils.notifications import message_internal_slack_group
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import check_worker_allowed_new_assignment
from orchestra.utils.task_lifecycle import get_role_from_counter
from orchestra.utils.task_lifecycle import is_worker_certified_for_task
from orchestra.utils.task_lifecycle import reassign_assignment


@transaction.atomic
def handle_staffing_response(worker, staffing_request_inquiry_id,
                             is_available=False):
    """
    Args:
        worker (orchestra.models.Worker):
            Worker instance that responsed to a staffing request inquiry
        staffing_request_inquiry_id (int):
            Id of a staffing_request_inquiry that is associated with a response
        is_available (boolean):
            Boolean that tells whether worker accepted an inquiry or not
    Returns:
        response (orchestra.models.StaffingResponse):
            StaffingResponse object that has been created for the worker
    """
    staffing_request_inquiry = get_object_or_None(
        StaffingRequestInquiry,
        communication_preference__worker=worker,
        id=staffing_request_inquiry_id
    )
    if staffing_request_inquiry is None:
        return None

    response = (StaffingResponse.objects
                .filter(request_inquiry=staffing_request_inquiry))
    if response.exists():
        response = response.first()
        if not is_available and response.is_winner:
            raise StaffingResponseException(
                'Cannot reject after accepting the task')
        # This update will be saved in re/assing_task if necessary.
        response.is_available = is_available

    else:
        response = StaffingResponse.objects.create(
            request_inquiry=staffing_request_inquiry,
            is_available=is_available)

    request = staffing_request_inquiry.request
    if (is_available and
            request.status != StaffBotRequest.Status.CLOSED.value):
        task_assignment = get_object_or_None(
            TaskAssignment,
            task=request.task,
            assignment_counter=request.required_role_counter
        )

        # if task assignment exists then reassign
        if task_assignment is not None:
            reassign_assignment(worker.id, task_assignment.id,
                                staffing_request_inquiry)
        # otherwise assign task
        else:
            assign_task(worker.id, request.task.id,
                        staffing_request_inquiry)

    response = (StaffingResponse.objects
                .filter(request_inquiry=staffing_request_inquiry)
                .first())
    check_responses_complete(staffing_request_inquiry.request)
    return response


def check_responses_complete(request):
    inquiries = (
        StaffingRequestInquiry.objects.filter(request=request)
    ).distinct()
    num_inquired_workers = len(
        set(inquiries.values_list(
            'communication_preference__worker__id', flat=True)
            )
    )
    responded_inquiries = inquiries.filter(
        responses__isnull=False).distinct()
    num_responded_workers = len(
        set(responded_inquiries.values_list(
            'communication_preference__worker__id', flat=True)
            )
    )

    responses = StaffingResponse.objects.filter(
        request_inquiry__request=request)
    if (num_responded_workers >= num_inquired_workers and
            not responses.filter(is_winner=True).exists()):
        request.status = StaffBotRequest.Status.CLOSED.value
        request.save()

        # notify that all workers have rejected a task
        message_experts_slack_group(
            request.task.project.slack_group_id,
            ('No worker has accepted to work on task {}'
             .format(request.task)))


def send_staffing_requests(
        worker_batch_size=settings.ORCHESTRA_STAFFBOT_WORKER_BATCH_SIZE,
        frequency=settings.ORCHESTRA_STAFFBOT_BATCH_FREQUENCY):
    staffbot = StaffBot()
    cutoff_datetime = timezone.now() - frequency
    requests = (
        StaffBotRequest.objects
        .filter(status=StaffBotRequest.Status.SENDING_INQUIRIES.value)
        .filter(Q(last_inquiry_sent__isnull=True) |
                Q(last_inquiry_sent__lte=cutoff_datetime)))

    for request in requests:
        send_request_inquiries(staffbot, request, worker_batch_size)


def _send_request_inquiries(staffbot, request, worker_batch_size,
                            worker_certifications):
    inquiries_sent = 0
    required_role = get_role_from_counter(request.required_role_counter)
    contacted_workers = set()

    for certification in worker_certifications:
        try:
            worker = certification.worker
            if worker.id in contacted_workers:
                continue

            contacted_workers.add(worker.id)
            check_worker_allowed_new_assignment(worker)
            if (is_worker_certified_for_task(worker, request.task,
                                             required_role,
                                             require_staffbot_enabled=True) and
                    not request.task.is_worker_assigned(worker)):
                staffbot.send_task_to_worker(worker, request)
                inquiries_sent += 1
            if inquiries_sent >= worker_batch_size:
                break

        except TaskStatusError:
            pass
        except TaskAssignmentError:
            pass

    # check whether all inquiries have been sent out.
    if inquiries_sent < worker_batch_size:
        message_experts_slack_group(
            request.task.project.slack_group_id,
            ('All staffing requests for task {} have been sent!'
             .format(request.task)))
        request.status = StaffBotRequest.Status.DONE_SENDING_INQUIRIES.value
    request.last_inquiry_sent = timezone.now()
    request.save()


def send_request_inquiries(staffbot, request, worker_batch_size):
    # Get Workers that haven't already received an inquiry.
    workers_with_inquiries = (StaffingRequestInquiry.objects.filter(
        request=request).distinct().values_list(
            'communication_preference__worker__id', flat=True))
    required_role = get_role_from_counter(request.required_role_counter)

    # Sort Worker Certifications by their staffing priority first,
    # and then randomly within competing staffing priorities.
    worker_certifications = (
        WorkerCertification
        .objects
        .exclude(worker__id__in=workers_with_inquiries)
        .filter(role=required_role,
                task_class=WorkerCertification.TaskClass.REAL,
                certification__in=(request.task
                                   .step.required_certifications.all()))
        .order_by('-staffing_priority', '?'))
    _send_request_inquiries(staffbot, request, worker_batch_size,
                            worker_certifications)


def get_available_requests(worker):
    # We want to show a worker only requests for which there is no
    # winner or for which they have not already replied.
    worker_provided_responses = StaffingResponse.objects.filter(
        request_inquiry__communication_preference__worker=worker)
    remaining_requests = (
        StaffBotRequest.objects
        .filter(inquiries__communication_preference__worker=worker)
        .exclude(status=StaffBotRequest.Status.CLOSED.value)
        .exclude(task__project__status=Project.Status.COMPLETED)
        .exclude(task__project__status=Project.Status.ABORTED)
        .exclude(task__status=Task.Status.COMPLETE)
        .exclude(task__status=Task.Status.ABORTED)
        .exclude(inquiries__responses__in=worker_provided_responses)
        .distinct())
    inquiries = (
        StaffingRequestInquiry.objects
        .filter(request__in=remaining_requests)
        .filter(communication_preference__worker=worker)
        .order_by('request__task__start_datetime'))
    # Because we might send multiple request inquiries to the same
    # worker for the same request (e.g., email and slack), we
    # deduplicate the inquiries so that we will return at most one
    # inquiry's worth of content here.
    request_ids = set()
    contexts = []
    staffbot = StaffBot()
    for inquiry in inquiries:
        if inquiry.request.id in request_ids:
            continue
        request_ids.add(inquiry.request.id)
        metadata = staffbot.get_staffing_request_metadata(inquiry)
        metadata['detailed_description'] = markdown(
            metadata['detailed_description'], extras=['target-blank-links'])
        metadata['reject_url'] += '?next={}'.format(
            reverse('orchestra:communication:available_staffing_requests'))
        contexts.append(metadata)
    return contexts


def warn_staffing_team_about_unstaffed_tasks():
    max_unstaffed_datetime = (
        timezone.now() - settings.ORCHESTRA_STAFFBOT_STAFFING_MIN_TIME)

    # Get all requests without winners
    task_values = (
        Task.objects.all()
        .filter(start_datetime__lt=max_unstaffed_datetime)
        .exclude(staffing_requests__inquiries__responses__is_winner=True)
        .exclude(status=Task.Status.COMPLETE)
        .exclude(status=Task.Status.ABORTED)
        .exclude(staffing_requests__isnull=True)
        .exclude(staffing_requests__inquiries__isnull=True)
        .order_by('-start_datetime')
        .values('staffing_requests__required_role_counter', 'id'))

    requests_to_notify = defaultdict(list)
    for task_value in task_values:
        required_role_counter = task_value[
            'staffing_requests__required_role_counter']
        request = (
            StaffBotRequest.objects.filter(
                task=task_value['id'],
                required_role_counter=required_role_counter)
            .order_by('-created_at'))[0]

        if request.created_at < max_unstaffed_datetime:
            requests_to_notify[request.task.step].append(request)

    for step, requests in requests_to_notify.items():
        message = '\n'.join([
            ('No winner request for task {} - {}! Created at {}.'
                .format(request.task.id, request.task, request.created_at))
            for request in requests])
        message_internal_slack_group(
            settings.ORCHESTRA_STAFFBOT_STAFFING_GROUP_ID, message)


def remind_workers_about_available_tasks():
    staffbot = StaffBot()
    workers = Worker.objects.all()
    for worker in workers:
        requests = get_available_requests(worker)
        # TODO(kkamalov): send out reminder only if last request was sent
        # at least ORCHESTRA_STAFFBOT_MIN_FOLLOWUP_TIME ago
        if len(requests):
            staffbot.send_worker_tasks_available_reminder(worker)
