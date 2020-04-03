import logging

from django.db import transaction

from orchestra.models import StaffBotRequest
from orchestra.models import StaffingResponse

logger = logging.getLogger(__name__)


@transaction.atomic
def mark_worker_as_winner(worker, task, required_role_counter,
                          staffing_request_inquiry):
    staffbot_request = (
        StaffBotRequest.objects
        .filter(task=task, required_role_counter=required_role_counter)
        .exclude(status=StaffBotRequest.Status.CLOSED.value)
        .order_by('-created_at'))

    # Check whether staffbot request was sent out for this task
    if not staffbot_request.exists():
        return

    if staffing_request_inquiry:
        staffbot_request = staffing_request_inquiry.request
    else:
        staffbot_request = staffbot_request.first()

    close_open_staffbot_requests(task)

    # If staffing request inquiry provided
    if staffing_request_inquiry:
        staffing_response = staffing_request_inquiry.responses.all()
    else:
        staffing_response = StaffingResponse.objects.filter(
            request_inquiry__request=staffbot_request,
            request_inquiry__communication_preference__worker=worker)

    if staffing_response.exists():
        staffing_response = staffing_response.first()
        staffing_response.is_available = True
        staffing_response.is_winner = True
        staffing_response.save()


@transaction.atomic
def close_open_staffbot_requests(task):
    CLOSED = StaffBotRequest.Status.CLOSED.value
    requests = task.staffing_requests.all()
    for request in requests:
        request.status = CLOSED
    StaffBotRequest.objects.bulk_update(requests, ['status'])
