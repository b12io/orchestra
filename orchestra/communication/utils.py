import logging

from django.db import transaction

from orchestra.models import CommunicationPreference
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse

logger = logging.getLogger(__name__)


@transaction.atomic
def mark_worker_as_winner(worker, task, required_role_counter,
                          staffing_request_inquiry):
    staffbot_request = (
        StaffBotRequest.objects
        .filter(task=task, required_role_counter=required_role_counter)
        .order_by('-created_at'))

    # Check whether staffbot request was sent out for this task
    if not staffbot_request.exists():
        return

    if staffing_request_inquiry:
        staffbot_request = staffing_request_inquiry.request
    else:
        staffbot_request = staffbot_request.first()

    staffbot_request.status = StaffBotRequest.Status.COMPLETE.value
    staffbot_request.save()

    # Mark everyone else as non-winner
    StaffingResponse.objects.filter(
        request_inquiry__request=staffbot_request).update(is_winner=False)

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
    else:
        # This branch occurs if a worker was assigned to a task that has
        # an open StaffBot Request, but StaffBot hasn't reached out
        # to the Worker yet. We fib a little and create in inquiry/response
        # for the worker so they can be marked as a winner.
        comm_pref = CommunicationPreference.objects.filter(
            worker=worker)
        if not comm_pref.exists():
            logger.error('Worker {} does not have a communication '
                         'preferences setup'.format(worker))
            return

        comm_pref = comm_pref.first()
        comm_method = StaffingRequestInquiry.CommunicationMethod.SLACK.value

        if not staffing_request_inquiry:
            staffing_request_inquiry = (
                StaffingRequestInquiry.objects
                .create(request=staffbot_request,
                        communication_preference=comm_pref,
                        communication_method=comm_method))

        StaffingResponse.objects.create(
            request_inquiry=staffing_request_inquiry,
            is_available=True,
            is_winner=True)
