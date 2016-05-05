from annoying.functions import get_object_or_None
from django.db import transaction

from orchestra.bots.errors import StaffingResponseException
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse
from orchestra.utils.task_lifecycle import assign_task


@transaction.atomic
def handle_staffing_response(worker, staffing_request_id, is_available=False):
    # TODO(kkamalov): add proper docstring
    staffing_request = get_object_or_None(
        StaffingRequestInquiry,
        communication_preference__worker=worker,
        id=staffing_request_id
    )
    if staffing_request is None:
        return None

    response = StaffingResponse.objects.filter(request=staffing_request)
    if response.exists():
        response = response.first()
        if not is_available and response.is_winner:
            raise StaffingResponseException(
                'Cannot reject after accepting the task')

        response.is_available = is_available

    else:
        response = StaffingResponse.objects.create(
            request=staffing_request,
            is_available=is_available)

    if (is_available and
            not StaffingResponse.objects.filter(
                request__task=staffing_request.task,
                request__required_role=staffing_request.required_role,
                is_winner=True).exists()):
        response.is_winner = True
        assign_task(worker.id,
                    staffing_request.task.id)

    response.save()
    return response
