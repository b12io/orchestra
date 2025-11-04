from django.urls import re_path

from orchestra.interface_api.project_management import views

app_name = 'project_management'

urlpatterns = [
    re_path(r'^projects/$',
            views.ProjectList.as_view(),
            name='projects'),

    re_path(r'^assign_task/$',
            views.assign_task_api,
            name='assign_task'),

    re_path(r'^complete_and_skip_task/$',
            views.complete_and_skip_task_api,
            name='complete_and_skip_task'),

    re_path(r'^create_subsequent_tasks/$',
            views.create_subsequent_tasks_api,
            name='create_subsequent_tasks'),

    re_path(r'^edit_slack_membership/$',
            views.edit_slack_membership_api,
            name='edit_slack_membership'),

    re_path(r'^unarchive_slack_channel/$',
            views.unarchive_slack_channel_api,
            name='unarchive_slack_channel'),

    re_path(r'^end_project/$',
            views.end_project_api,
            name='end_project'),

    re_path(r'^set_project_status/$',
            views.set_project_status_api,
            name='set_project_status'),

    re_path(r'^project_information/$',
            views.project_information_api,
            name='project_information'),

    re_path(r'^reassign_assignment/$',
            views.reassign_assignment_api,
            name='reassign_assignment'),

    re_path(r'^revert_task/$',
            views.revert_task_api,
            name='revert_task'),

    re_path(r'^staff_task/$',
            views.staff_task,
            name='staff_task'),
]
