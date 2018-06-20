from django.conf.urls import url

from orchestra.todos.views import TodoDetail
from orchestra.todos.views import TodoList
from orchestra.todos.views import TodoListTemplateDetail
from orchestra.todos.views import TodoListTemplateList

urlpatterns = [
    url(r'^todo/$',
        TodoList.as_view(), name='todos'),
    url(r'^todo/(?P<pk>[0-9]+)/$',
        TodoDetail.as_view(), name='todo'),
    url(r'^todolist_templates/$',
        TodoListTemplateList.as_view(), name='todolist_templates'),
    url(r'^todolist_template/(?P<pk>[0-9]+)/$',
        TodoListTemplateDetail.as_view(), name='todolist_template'),
]
