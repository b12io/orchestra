from django.urls import re_path

from orchestra.communication.views import accept_staffing_request_inquiry
from orchestra.communication.views import available_staffing_requests
from orchestra.communication.views import reject_staffing_request_inquiry

app_name = 'communication'

urlpatterns = [
    # Interface API
    re_path(r'^accept_staffing_request_inquiry/(?P<staffing_request_inquiry_id>[0-9]+)/$',  # noqa
        accept_staffing_request_inquiry,
        name='accept_staffing_request_inquiry'),
    re_path(r'^reject_staffing_request_inquiry/(?P<staffing_request_inquiry_id>[0-9]+)/$',  # noqa
        reject_staffing_request_inquiry,
        name='reject_staffing_request_inquiry'),
    re_path(r'^available_staffing_requests/',
        available_staffing_requests,
        name='available_staffing_requests'),
]
