from django.conf.urls import url

from orchestra.communication.views import accept_staffing_request
from orchestra.communication.views import reject_staffing_request


urlpatterns = [
    # Interface API
    url(r'^accept_request/(?P<pk>[0-9]+)/$',
        accept_staffing_request, name='accept_staffing_request'),
    url(r'^reject_request/(?P<pk>[0-9]+)/$',
        reject_staffing_request, name='reject_staffing_request'),
]
