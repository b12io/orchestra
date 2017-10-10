from django.conf.urls import url

from orchestra.todos.views import TodoDetail
from orchestra.todos.views import TodoList

urlpatterns = [
    url(r'^todo/$',
        TodoList.as_view(), name='todo'),
    url(r'^todo/(?P<pk>[0-9]+)/$',
        TodoDetail.as_view(), name='todo'),
]
