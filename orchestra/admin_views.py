from datetime import datetime
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render
from django.utils.encoding import force_text
from django.utils.text import capfirst
from orchestra.models import Project
from orchestra.orchestra_api import get_project_information

import re


@staff_member_required
def project_details(request, project_id):
    info = get_project_information(project_id)
    project_data = _prettify_project_details(info['project'],
                                             info['tasks'],
                                             info['steps'])

    # opts, module_name, site_url, and has_permission are django admin related
    # variables that are used to help build the breadcrumbs and top bar content
    return render(request, 'orchestra/project_details.html', {
        'project': project_data['project'],
        'tasks': project_data['tasks'],
        'opts': Project._meta,
        'module_name': capfirst(force_text(Project._meta.verbose_name_plural)),
        'site_url': '/',
    })


def _prettify_project_details(project, tasks_data, steps):
    project['start_datetime'] = datetime.strptime(project['start_datetime'],
                                                  '%Y-%m-%dT%H:%M:%S.%fZ')

    # Clean up the project_data dict's keys so they will display nicely
    url_regex = re.compile(r"url", re.IGNORECASE)
    id_regex = re.compile(r"id", re.IGNORECASE)
    for key, value in project['project_data'].items():
        new_key = capfirst(key).replace('_', ' ')
        new_key = url_regex.sub('URL', new_key)
        new_key = id_regex.sub('ID', new_key)
        project['project_data'][new_key] = project['project_data'].pop(key)

    # Steps is an ordered list of step tuples.
    # The first tuple element is the step slug and the second is the step
    # description.
    tasks = []

    # Tie the tasks to their relevant steps so they can be displayed in order
    for step_slug, step_description in steps:
        task = tasks_data.get(step_slug, {
            'step_slug': step_slug,
            'status': 'Not started',
            'latest_data': {},
        })

        task['step_description'] = step_description

        # Assignment times need to be formatted more nicely
        for assignment in task.get('assignments', []):
            new_datetime = datetime.strptime(assignment['start_datetime'],
                                             '%Y-%m-%dT%H:%M:%S.%fZ')
            assignment['start_datetime'] = new_datetime

        tasks.append(task)
    return {'project': project,
            'tasks': tasks}
