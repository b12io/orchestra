from annoying.functions import get_object_or_None
from django.db import transaction

from orchestra.bots.errors import StaffingResponseException
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import TaskAssignmentError
from orchestra.bots.staffbot import StaffBot
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.utils.notifications import message_experts_slack_group
from orchestra.utils.task_lifecycle import reassign_assignment
from orchestra.utils.task_lifecycle import assign_task

from orchestra.utils.task_lifecycle import check_worker_allowed_new_assignment
from orchestra.utils.task_lifecycle import get_role_from_counter
from orchestra.utils.task_lifecycle import is_worker_certified_for_task

WORKER_BATCH_SIZE = 5


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


def send_staffing_requests(worker_batch_size=WORKER_BATCH_SIZE):
    staffbot = StaffBot()
    requests = (StaffBotRequest.objects.filter(
        status=StaffBotRequest.Status.PROCESSING.value))

    for request in requests:
        send_request_inquiries(staffbot, request, worker_batch_size)


def send_request_inquiries(staffbot, request, worker_batch_size):

    # get names of workers that that already received inquiry
    worker_usernames = (StaffingRequestInquiry.objects.filter(
        request=request).values_list(
            'communication_preference__worker__user__username', flat=True))
    workers = (Worker.objects
               .exclude(user__username__in=worker_usernames)
               .order_by('?'))
    required_role = get_role_from_counter(request.required_role_counter)
    inquiries_sent = 0

    for worker in workers:
        try:
            check_worker_allowed_new_assignment(worker)
            if (is_worker_certified_for_task(worker, request.task,
                                             required_role) and
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
        request.save()
