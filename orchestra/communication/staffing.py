from annoying.functions import get_object_or_None
from django.db import transaction

from orchestra.models import StaffingRequest
from orchestra.models import StaffingResponse
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import remove_worker_from_task


@transaction.atomic
def handle_staffing_response(worker, staffing_request_id, is_available=False):
    # TODO(kkamalov): add proper docstring
    staffing_request = get_object_or_None(
        StaffingRequest,
        communication_preference__worker=worker,
        id=staffing_request_id
    )
    if staffing_request is None:
        return None

    response = StaffingResponse.objects.filter(request=staffing_request)
    if response.exists():
        response = response.first()
        response.is_available = is_available

        if not is_available and response.is_winner:
            remove_worker_from_task(
                worker.user.username,
                staffing_request.task.id)
            response.is_winner = False
    else:
        response = StaffingResponse.objects.create(
            request=staffing_request,
            is_available=is_available)

    if (is_available and
            not StaffingResponse.objects.filter(is_winner=True).exists()):
        response.is_winner = True
        assign_task(worker.id,
                    staffing_request.task.id)

    response.save()
    return response
