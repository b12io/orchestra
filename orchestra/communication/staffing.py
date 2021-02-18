from annoying.functions import get_object_or_None
from collections import defaultdict
from datetime import timedelta
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
from orchestra.models import CommunicationPreference
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse
from orchestra.models import Task
from orchestra.models import Project
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.models import WorkerAvailability
from orchestra.models import WorkerCertification
from orchestra.utils.datetime_utils import first_day_of_the_week
from orchestra.utils.time_tracking import time_entry_hours_worked
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


def address_staffing_requests(
        worker_batch_size=settings.ORCHESTRA_STAFFBOT_WORKER_BATCH_SIZE,
        frequency=settings.ORCHESTRA_STAFFBOT_BATCH_FREQUENCY):
    staffbot = StaffBot()
    cutoff_datetime = timezone.now() - frequency
    requests = (
        StaffBotRequest.objects
        .filter(status__in=[
            StaffBotRequest.Status.SENDING_INQUIRIES.value,
            StaffBotRequest.Status.DONE_SENDING_INQUIRIES.value])
        .filter(Q(last_inquiry_sent__isnull=True) |
                Q(last_inquiry_sent__lte=cutoff_datetime))
        .order_by('-task__project__priority', 'created_at'))

    for request in requests:
        staff_or_send_request_inquiries(staffbot, request, worker_batch_size)


def _is_worker_assignable(worker, task, required_role):
    try:
        check_worker_allowed_new_assignment(worker)
        if (is_worker_certified_for_task(worker, task,
                                         required_role,
                                         require_staffbot_enabled=True)
                and not task.is_worker_assigned(worker)):
            return True
    except TaskStatusError:
        pass
    except TaskAssignmentError:
        pass
    return False


def _can_handle_more_work_today(worker, task):
    can_handle_more_hours = False
    today = timezone.now().date()
    today_abbreviation = ['mon', 'tues', 'wed', 'thurs', 'fri', 'sat', 'sun'][
        today.weekday()]
    availability = WorkerAvailability.objects.filter(
        worker=worker,
        week=first_day_of_the_week()).first()
    task_hours = task.get_assignable_hours()
    if availability is not None and task_hours is not None:
        desired_hours = getattr(
            availability, 'hours_available_{}'.format(today_abbreviation))
        responses = StaffingResponse.objects.filter(
            request_inquiry__communication_preference__worker=worker,
            is_winner=True,
            created_at__gte=today,
            created_at__lt=today + timedelta(days=1)
        )
        hours_assigned = [
            (response.request_inquiry.request.task.get_assignable_hours(),
             response.request_inquiry.request.task)
            for response in responses]
        hours_assigned = [
            (hours, task) for (hours, task) in hours_assigned
            if hours is not None]
        max_tasks = settings.ORCHESTRA_MAX_AUTOSTAFF_TASKS_PER_DAY
        # To estimate how much someone worked today, we add:
        # - the number of assignable hours they were assigned today
        # - the number of hours they tracked (excluding work completed
        #   on today's newly assigned work, to avoid double-counting)
        # We do not attempt to estimate the amount of "unexpected" work,
        #   like iteration time on an old project the expert has learned
        #   about over Slack but hasn't yet logged for the day.
        sum_hours_assigned = sum(hours for (hours, task) in hours_assigned)
        sum_hours_worked = time_entry_hours_worked(
            today, worker, excluded_tasks=[
                task for (hours, task) in hours_assigned])
        can_handle_more_hours = (
            (len(hours_assigned) + 1 <= max_tasks)
            and (sum_hours_assigned
                 + sum_hours_worked
                 + task_hours <= desired_hours))
    return can_handle_more_hours


def _attempt_to_automatically_staff(staffbot, request, worker_certifications):
    successfully_staffed = False
    required_role = get_role_from_counter(request.required_role_counter)
    attempted_workers = set()
    new_task_available_type = (
        CommunicationPreference.CommunicationType.NEW_TASK_AVAILABLE.value)
    previously_opted_in_method = (
        StaffingRequestInquiry.CommunicationMethod.PREVIOUSLY_OPTED_IN.value)
    for certification in worker_certifications:
        worker = certification.worker
        if worker.id in attempted_workers:
            continue
        attempted_workers.add(worker.id)
        if (_is_worker_assignable(worker, request.task, required_role)
                and _can_handle_more_work_today(worker, request.task)):
            communication_preference = (
                CommunicationPreference.objects.get(
                    communication_type=new_task_available_type,
                    worker=worker))
            staffing_request_inquiry = StaffingRequestInquiry.objects.create(
                communication_preference=communication_preference,
                communication_method=previously_opted_in_method,
                request=request)
            handle_staffing_response(
                worker, staffing_request_inquiry.id, is_available=True)
            successfully_staffed = True
            break
    return successfully_staffed


def _send_request_inquiries(staffbot, request, worker_batch_size,
                            worker_certifications):
    inquiries_sent = 0
    required_role = get_role_from_counter(request.required_role_counter)
    contacted_workers = set()
    for certification in worker_certifications:
        worker = certification.worker
        if worker.id in contacted_workers:
            continue
        contacted_workers.add(worker.id)
        if _is_worker_assignable(worker, request.task, required_role):
            staffbot.send_task_to_worker(worker, request)
            inquiries_sent += 1
        if inquiries_sent >= worker_batch_size:
            break

    # check whether all inquiries have been sent out.
    if inquiries_sent < worker_batch_size:
        message_experts_slack_group(
            request.task.project.slack_group_id,
            ('All staffing requests for task {} have been sent!'
             .format(request.task)))
        request.status = StaffBotRequest.Status.DONE_SENDING_INQUIRIES.value
    request.last_inquiry_sent = timezone.now()
    request.save()


def staff_or_send_request_inquiries(staffbot, request, worker_batch_size):
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
        .filter(role=required_role,
                task_class=WorkerCertification.TaskClass.REAL,
                certification__in=(request.task
                                   .step.required_certifications.all()))
        .order_by('-staffing_priority', '?'))
    available_worker_certifications = (
        worker_certifications
        .filter(worker__availabilities__week=first_day_of_the_week()))
    uninquired_worker_certifications = (
        worker_certifications
        .exclude(worker__id__in=workers_with_inquiries))
    successfully_staffed = _attempt_to_automatically_staff(
        staffbot, request, available_worker_certifications)
    sending_inquiries = StaffBotRequest.Status.SENDING_INQUIRIES.value
    if ((not successfully_staffed)
            and (request.status == sending_inquiries)):
        _send_request_inquiries(staffbot,
                                request,
                                worker_batch_size,
                                uninquired_worker_certifications)


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
        .order_by('-request__task__project__priority', 'request__created_at'))
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
