from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import render

from orchestra.bots.errors import StaffingResponseException
from orchestra.models import Worker
from orchestra.communication.staffing import handle_staffing_response


@login_required
def accept_staffing_request(request, staffing_request_id):
    worker = Worker.objects.get(user=request.user)
    try:
        response = handle_staffing_response(
            worker, staffing_request_id, is_available=True)
    except StaffingResponseException:
        return render(request,
                      'communication/staffing_response_not_permitted.html',
                      {})
    if response is None:
        raise Http404
    return render(request, 'communication/staffing_request_accepted.html',
                  {
                      'response': response,
                  })


@login_required
def reject_staffing_request(request, staffing_request_id):
    worker = Worker.objects.get(user=request.user)
    response = handle_staffing_response(
        worker, staffing_request_id, is_available=False)
    if response is None:
        raise Http404
    return render(request, 'communication/staffing_request_rejected.html',
                  {})
