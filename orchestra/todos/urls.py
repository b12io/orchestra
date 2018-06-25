from django.conf.urls import url

from orchestra.todos.views import TodoDetail
from orchestra.todos.views import TodoList
from orchestra.todos.views import TodoListTemplateDetail
from orchestra.todos.views import TodoListTemplateList
import orchestra.todos.views as views

urlpatterns = [
    url(r'^todo/$',
        TodoList.as_view(), name='todos'),
    url(r'^todo/(?P<pk>[0-9]+)/$',
        TodoDetail.as_view(), name='todo'),
    url(r'^todolist_templates/$',
        TodoListTemplateList.as_view(), name='todolist_templates'),
    url(r'^todolist_template/(?P<pk>[0-9]+)/$',
        TodoListTemplateDetail.as_view(), name='todolist_template'),
    url(r'^add_todos_from_todolist_template/$',
        views.add_todos_from_todolist_template,
        name='add_todos_from_todolist_template'),
]
