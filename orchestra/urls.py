from django.conf import settings
from django.conf.urls import include
from django.conf.urls import url
from django.views.generic import RedirectView

from orchestra.views import index
from orchestra.views import status

urlpatterns = [
    url(r'^api/',
        include('orchestra.api_urls', namespace='orchestra')),
    url(r'^app/?', index, name='index'),
    url(r'^status/', status, name='status'),
    url(r'^favicon.ico/$', RedirectView.as_view(
        url=settings.STATIC_URL + 'orchestra/icons/favicon.ico',
        permanent=True),
        name='favicon'),
    url(r'', include('orchestra.accounts.urls'))
]
