from django.conf.urls import url

from orchestra.communication.views import accept_staffing_request_inquiry
from orchestra.communication.views import reject_staffing_request_inquiry


urlpatterns = [
    # Interface API
    url(r'^accept_staffing_request_inquiry/(?P<staffing_request_inquiry_id>[0-9]+)/$',  # noqa
        accept_staffing_request_inquiry,
        name='accept_staffing_request_inquiry'),
    url(r'^reject_staffing_request_inquiry/(?P<staffing_request_inquiry_id>[0-9]+)/$',  # noqa
        reject_staffing_request_inquiry,
        name='reject_staffing_request_inquiry'),
]
