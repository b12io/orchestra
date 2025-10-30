from django.conf.urls import include
from django.urls import re_path

from orchestra.views import index
from orchestra.views import newindex
from orchestra.views import status

app_name = 'orchestra'

urlpatterns = [
    re_path(r'^api/',
        include('orchestra.api_urls', namespace='orchestra')),
    re_path(r'^communication/',
        include('orchestra.communication.urls',
                namespace='communication')),
    re_path(r'^newapp/?', newindex, name='newindex'),
    re_path(r'^app/?', index, name='index'),
    re_path(r'', include('orchestra.accounts.urls')),
    re_path(r'^bots/', include('orchestra.bots.urls', namespace='bots')),
    re_path(r'^todos/', include('orchestra.todos.urls', namespace='todos')),

    # Health check status
    re_path(r'^status/', status, name='status'),
]
