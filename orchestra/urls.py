from django.conf.urls import include
from django.conf.urls import url

from orchestra.views import index
from orchestra.views import newindex
from orchestra.views import status

app_name = 'orchestra'

urlpatterns = [
    url(r'^api/',
        include('orchestra.api_urls', namespace='orchestra')),
    url(r'^communication/',
        include('orchestra.communication.urls',
                namespace='communication')),
    url(r'^newapp/?', newindex, name='newindex'),
    url(r'^app/?', index, name='index'),
    url(r'', include('orchestra.accounts.urls')),
    url(r'^bots/', include('orchestra.bots.urls', namespace='bots')),
    url(r'^todos/', include('orchestra.todos.urls', namespace='todos')),

    # Health check status
    url(r'^status/', status, name='status'),
]
