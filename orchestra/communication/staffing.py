from annoying.functions import get_object_or_None
from datetime import timedelta
from django.db.models import Count
from django.conf import settings
from django.core.urlresolvers import reverse
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from markdown2 import markdown

from orchestra.bots.errors import StaffingResponseException
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import TaskAssignmentError
from orchestra.bots.staffbot import StaffBot
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import WorkerCertification
from orchestra.utils.notifications import message_experts_slack_group
from orchestra.utils.task_lifecycle import reassign_assignment
from orchestra.utils.task_lifecycle import assign_task

from orchestra.utils.task_lifecycle import check_worker_allowed_new_assignment
from orchestra.utils.task_lifecycle import get_role_from_counter
from orchestra.utils.task_lifecycle import is_worker_certified_for_task


MAX_REQUEST_COUNT = 3
MAX_TIME_NO_RESPONSE = 300 # Minutes or 5 hours
RESEND_TIME = 60 # Minutes or 1 hours
STAFFING_GROUP_ID = 'G7R9Q24TZ'


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

    # TODO(kkamalov): add proper docstring
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

        response.is_available = is_available

    else:
        response = StaffingResponse.objects.create(
            request_inquiry=staffing_request_inquiry,
            is_available=is_available)

    if (is_available and
            not StaffingResponse.objects.filter(
                request_inquiry__request=staffing_request_inquiry.request,
                is_winner=True).exists()):
        response.is_winner = True
        request = staffing_request_inquiry.request
        request.status = StaffBotRequest.Status.COMPLETE.value
        request.save()

        task_assignment = get_object_or_None(
            TaskAssignment,
            task=request.task,
            assignment_counter=request.required_role_counter
        )

        # if task assignment exists then reassign
        if task_assignment is not None:
            reassign_assignment(worker.id, task_assignment.id)
        # otherwise assign task
        else:
            assign_task(worker.id, request.task.id)

    response.save()
    check_responses_complete(staffing_request_inquiry.request)
    return response


def check_responses_complete(request):
    # check all responses have been complete
    responses = StaffingResponse.objects.filter(
        request_inquiry__request=request)
    request_inquiries = StaffingRequestInquiry.objects.filter(
        request=request)
    if (responses.count() == request_inquiries.count() and
            not responses.filter(is_winner=True).exists()):
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
        .filter(status=StaffBotRequest.Status.PROCESSING.value)
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
        request.status = StaffBotRequest.Status.COMPLETE.value
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
    won_responses = StaffingResponse.objects.filter(is_winner=True)
    worker_provided_responses = StaffingResponse.objects.filter(
        request_inquiry__communication_preference__worker=worker)
    remaining_requests = (
        StaffBotRequest.objects
        .filter(inquiries__communication_preference__worker=worker)
        .exclude(inquiries__responses__in=won_responses)
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
            metadata['detailed_description'])
        metadata['reject_url'] += '?next={}'.format(
            reverse('orchestra:communication:available_staffing_requests'))
        contexts.append(metadata)
    return contexts


def get_inquiries_per_worker_count(request):
    inq_count = (request.inquiries.all()
                 .values('communication_preference__worker')
                 .annotate(Count('communication_preference__worker')))
    return inq_count[0]['communication_preference__worker__count']


def check_unstaffed_tasks():
    # Get all requests without winners
    task_values = (
        Task.objects.all()
        .filter(staffing_requests__inquiries__responses__is_winner=False)
        .exclude(staffing_requests__isnull=True)
        .exclude(staffing_requests__inquiries__isnull=True)
        .order_by('-start_datetime')
        .values('staffing_requests__required_role_counter', 'id')
        .annotate(Count('staffing_requests__id')))

    for task_value in task_values:
        if task_value['staffing_requests__id__count'] > MAX_REQUEST_COUNT:
            # Send to #staffing channel.
            message_experts_slack_group(
                STAFFING_GROUP_ID,
                ('No winner request for task {}!'
                 .format(request.task)))
            continue
        required_role_counter = task_value[
            'staffing_requests__required_role_counter']
        request = (
            StaffBotRequest.objects.filter(
                task=task_value['id'],
                required_role_counter=required_role_counter)
            .order_by('-created_at'))[0]

        if request.created_at < timezone.now() - timedelta(
                minutes=MAX_TIME_NO_RESPONSE):
            message_experts_slack_group(
                STAFFING_GROUP_ID,
                ('No winner request for task {}! Created at {}'
                 .format(request.task, request.created_at)))
            continue


def experts_followup():
    # Get all requests without winners
    requests = StaffBotRequest.objects.filter(
        inquiries__responses__is_winner=False).order_by(
            '-last_inquiry_sent')

    for request in requests:
        if not request.last_inquiry_sent:
            continue
        if request.last_inquiry_sent < timezone.now() - timedelta(
                minutes=RESEND_TIME):
            # resend
            pass
    pass
