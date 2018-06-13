from django.conf.urls import url

from orchestra.todos.views import TodoDetail
from orchestra.todos.views import TodoList
from orchestra.todos.views import ChecklistTemplateDetail
from orchestra.todos.views import ChecklistTemplateList

urlpatterns = [
    url(r'^checklists/$',
        ChecklistTemplateList.as_view(), name='checklists'),
    url(r'^checklist/$',
        ChecklistTemplateDetail.as_view(), name='checklist'),
    url(r'^todo/$',
        TodoList.as_view(), name='todos'),
    url(r'^todo/(?P<pk>[0-9]+)/$',
        TodoDetail.as_view(), name='todo'),
]
