from annoying.functions import get_object_or_None
from django.db import transaction

from orchestra.models import StaffingRequest
from orchestra.models import StaffingResponse


@transaction.atomic
def handle_staffing_response(worker, pk, is_available):
    """
    """
    staffing_request = get_object_or_None(StaffingRequest,
                                          pk=pk)
    if staffing_request is None:
        return None

    response = StaffingResponse.objects.filter(request=staffing_request)
    if response.exists():
        response = response.first()
        response.is_available = is_available

        if not is_available:
            response.is_winner = False
    else:
        response = StaffingResponse.objects.create(
            request=staffing_request,
            is_available=is_available)

    if (is_available and
            not StaffingResponse.objects.filter(is_winner=True).exists()):
        # TODO(kkamalov): create a TaskAssignment object
        response.is_winner = True

    response.save()
    return response
