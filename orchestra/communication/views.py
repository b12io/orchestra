from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.http import HttpResponseRedirect
from django.shortcuts import render

from orchestra.bots.errors import StaffingResponseException
from orchestra.communication.staffing import get_available_requests
from orchestra.communication.staffing import handle_staffing_response
from orchestra.models import Worker


@login_required
def accept_staffing_request_inquiry(request,
                                    staffing_request_inquiry_id):
    worker = Worker.objects.get(user=request.user)
    response = handle_staffing_response(
        worker, staffing_request_inquiry_id, is_available=True)

    if response is None:
        raise Http404
    return render(request, 'communication/staffing_request_accepted.html',
                  {
                      'response': response,
                  })


@login_required
def reject_staffing_request_inquiry(request,
                                    staffing_request_inquiry_id):
    worker = Worker.objects.get(user=request.user)
    try:
        response = handle_staffing_response(
            worker, staffing_request_inquiry_id, is_available=False)
    except StaffingResponseException:
        return render(request,
                      'communication/staffing_response_not_permitted.html',
                      {})
    if response is None:
        raise Http404

    next_path = request.GET.get('next')
    if next_path:
        return HttpResponseRedirect(next_path)
    else:
        return render(request, 'communication/staffing_request_rejected.html',
                      {})


@login_required
def available_staffing_requests(request):
    worker = Worker.objects.get(user=request.user)
    return render(request, 'communication/available_staffing_requests.html',
                  {
                      'requests': get_available_requests(worker),
                  })
