from rest_framework import routers
from django.conf.urls import include
from django.conf.urls import url

from orchestra.project_api.views import assign_worker_to_task
from orchestra.project_api.views import create_project
from orchestra.project_api.views import project_details_url
from orchestra.project_api.views import project_information
from orchestra.project_api.views import workflow_types
from orchestra.project_api.views import message_project_team
from orchestra.project_api.views import TodoApiViewset
from orchestra.views import TimeEntryDetail
from orchestra.views import TimeEntryList
from orchestra.views import dashboard_tasks
from orchestra.views import get_timer
from orchestra.views import new_task_assignment
from orchestra.views import save_task_assignment
from orchestra.views import start_timer
from orchestra.views import status
from orchestra.views import stop_timer
from orchestra.views import submit_task_assignment
from orchestra.views import task_assignment_information
from orchestra.views import update_timer
from orchestra.views import upload_image

app_name = 'api'

urlpatterns = [
    # Interface API
    url(r'^interface/dashboard_tasks/$',
        dashboard_tasks, name='dashboard_tasks'),

    url(r'^interface/task_assignment_information/$',
        task_assignment_information,
        name='task_assignment_information'),

    url(r'^interface/save_task_assignment/$',
        save_task_assignment,
        name='save_task_assignment'),

    url(r'^interface/submit_task_assignment/$',
        submit_task_assignment,
        name='submit_task_assignment'),

    url(r'^interface/new_task_assignment/(?P<task_type>\w+)/$',
        new_task_assignment,
        name='new_task_assignment'),

    url(r'^interface/upload_image/$',
        upload_image,
        name='upload_image'),

    url(r'^interface/time_entries/$',
        TimeEntryList.as_view(), name='time_entries'),

    url(r'^interface/time_entries/(?P<pk>[0-9]+)/$',
        TimeEntryDetail.as_view(), name='time_entry'),

    url(r'^interface/timer/start/$', start_timer, name='start_timer'),
    url(r'^interface/timer/stop/$', stop_timer, name='stop_timer'),
    url(r'^interface/timer/$', get_timer, name='get_timer'),
    url(r'^interface/timer/update/$', update_timer, name='update_timer'),

    url(r'^interface/project_management/',
        include('orchestra.interface_api.project_management.urls',
                namespace='project_management')),

    # Client API
    url(r'^project/project_information/$',
        project_information,
        name='project_information'),
    url(r'^project/create_project/$',
        create_project,
        name='create_project'),
    url(r'^project/workflow_types/$',
        workflow_types,
        name='workflow_types'),
    url(r'^project/project_details_url/$',
        project_details_url,
        name='project_details_url'),
    url(r'^project/assign_worker_to_task/$',
        assign_worker_to_task,
        name='assign_worker_to_task'),
    url(r'^status/$',
        status,
        name='status'),
    url(r'^project/message_project_team',
        message_project_team,
        name='message_project_team'),
]

router = routers.SimpleRouter()
router.register(
    r'project/todo-api', TodoApiViewset, basename='todo-api'
)

urlpatterns += router.urls
