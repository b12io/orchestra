from orchestra.models import CommunicationPreference
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse

import logging
logger = logging.getLogger(__name__)


def mark_worker_as_winner(worker, task, required_role_counter,
                          staffing_request_inquiry):
    staffbot_request = StaffBotRequest.objects.filter(
        task=task, required_role_counter=required_role_counter)

    # Check whether staffbot request was sent out for this task
    if not staffbot_request.exists():
        return

    staffbot_request = staffbot_request.first()
    if staffing_request_inquiry:
        staffbot_request = staffing_request_inquiry.request
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
        staffing_response.is_winner = True
        staffing_response.save()
    else:
        comm_pref = CommunicationPreference.objects.filter(
            worker=worker)
        if not comm_pref.exists():
            logger.error('Worker {} does not have a communication '
                         'preferences setup'.format(worker))
            return

        comm_pref = comm_pref.first()
        comm_method = StaffingRequestInquiry.CommunicationMethod.SLACK.value

        inquiry = StaffingRequestInquiry.objects.create(
            request=staffbot_request,
            communication_preference=comm_pref,
            communication_method=comm_method)

        StaffingResponse.objects.create(
            request_inquiry=inquiry,
            is_available=True,
            is_winner=True)
