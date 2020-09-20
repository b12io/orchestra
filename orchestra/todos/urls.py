from django.conf.urls import url
from rest_framework import routers

from orchestra.todos.views import TodoQADetail
from orchestra.todos.views import TodoQAList
from orchestra.todos.views import TodoViewset
from orchestra.todos.views import TodoListTemplateDetail
from orchestra.todos.views import TodoListTemplateList
import orchestra.todos.views as views

app_name = 'todos'

urlpatterns = [
    url(r'^todo_qa/$',
        TodoQAList.as_view(), name='todo_qas'),
    url(r'^todo_qa/(?P<pk>[0-9]+)/$',
        TodoQADetail.as_view(), name='todo_qa'),
    url(r'^todolist_templates/$',
        TodoListTemplateList.as_view(), name='todolist_templates'),
    url(r'^todolist_template/(?P<pk>[0-9]+)/$',
        TodoListTemplateDetail.as_view(), name='todolist_template'),
    url(r'^update_todos_from_todolist_template/$',
        views.update_todos_from_todolist_template,
        name='update_todos_from_todolist_template'),
    url(r'^worker_task_recent_todo_qas/$',
        views.worker_task_recent_todo_qas,
        name='worker_task_recent_todo_qas'),
    url(r'^todolist_template/(?P<pk>[0-9]+)/import$',
        views.ImportTodoListTemplateFromSpreadsheet.as_view(),
        name='import_todo_list_template_from_spreadsheet'),
]

router = routers.SimpleRouter()
router.register(
    r'todo', TodoViewset, basename='todos'
)

urlpatterns += router.urls
