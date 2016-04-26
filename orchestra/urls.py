from django.conf.urls import include
from django.conf.urls import url

from orchestra.views import index
from orchestra.views import OrchestraRegistrationView
from orchestra.views import status


urlpatterns = [
    url(r'^api/',
        include('orchestra.api_urls', namespace='orchestra')),
    url(r'^app/?', index, name='index'),
    url(r'^status/', status, name='status'),

    # We have to override the register endpoint to emit the
    # `orchestra_user_registered` signal
    url(r'^accounts/register/$',
        OrchestraRegistrationView.as_view(),
        name='registration_register'),
]
