from django.conf.urls import include
from django.conf.urls import url

from orchestra.views import index
from orchestra.views import status

urlpatterns = [
    url(r'^api/',
        include('orchestra.api_urls', namespace='orchestra')),
    url(r'^communication/',
        include('orchestra.communication.urls',
                namespace='communication')),
    url(r'^app/?', index, name='index'),
    url(r'', include('orchestra.accounts.urls')),
    url(r'^bots/', include('orchestra.bots.urls', namespace='bots')),

    # Health check status
    url(r'^status/', status, name='status'),
]
