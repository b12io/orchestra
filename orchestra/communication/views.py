from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from orchestra.models import Worker
from orchestra.communication.staffing import handle_staffing_response


@login_required
def accept_staffing_request(request, pk):
    worker = Worker.objects.get(user=request.user)
    response = handle_staffing_response(worker, pk, True)
    return render(request, 'communication/staffing_request_accepted.html',
                  {'is_winner': response.is_winner})


@login_required
def reject_staffing_request(request, pk):
    worker = Worker.objects.get(user=request.user)
    handle_staffing_response(worker, pk, False)
    return render(request, 'communication/staffing_request_rejected.html',
                  {})
