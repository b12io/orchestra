import base64
import json
import os

from collections import defaultdict

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from jsonview.decorators import json_view
from jsonview.exceptions import BadRequest
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import WorkerCertificationError
from orchestra.core.errors import NoTaskAvailable
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import IllegalTaskSubmission
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.workflow import get_workflows
from orchestra.utils.s3 import upload_editor_image
from orchestra.utils.task_lifecycle import save_task
from orchestra.utils.task_lifecycle import submit_task
from orchestra.utils.task_lifecycle import tasks_assigned_to_worker
from orchestra.utils.task_lifecycle import get_new_task_assignment
from orchestra.utils.task_lifecycle import get_task_overview_for_worker
from orchestra.utils.task_lifecycle import worker_assigned_to_rejected_task
from orchestra.utils.task_lifecycle import worker_assigned_to_max_tasks
from orchestra.utils.task_lifecycle import worker_has_reviewer_status

import logging

logger = logging.getLogger(__name__)


@login_required
def index(request):
    javascript_includes = []
    stylesheet_includes = []
    orchestra_arguments = {
        'angular_modules': [],
        'angular_directives': defaultdict(lambda: defaultdict(lambda: {}))}

    for slug, workflow in iter(get_workflows().items()):
        for step in workflow.get_human_steps():
            # Preserve js and stylesheet order while removing duplicates
            for js in step.user_interface.get('javascript_includes', []):
                if js not in javascript_includes:
                    javascript_includes.append(js)
            for style in step.user_interface.get('stylesheet_includes', []):
                if style not in stylesheet_includes:
                    stylesheet_includes.append(style)

            if step.user_interface.get('angular_module'):
                orchestra_arguments['angular_modules'].append(
                    step.user_interface['angular_module'])

            if step.user_interface.get('angular_directive'):
                orchestra_arguments['angular_directives'][workflow.slug][step.slug] = (  # noqa
                    step.user_interface['angular_directive'])

    return render(request, 'orchestra/index.html', {
        'javascript_includes': javascript_includes,
        'stylesheet_includes': stylesheet_includes,
        'orchestra_arguments': json.dumps(orchestra_arguments)})


@json_view
@login_required
def dashboard_tasks(request):
    worker = Worker.objects.get(user=request.user)
    tasks = tasks_assigned_to_worker(worker)
    prevent_new_tasks = (worker_assigned_to_rejected_task(worker) or
                         worker_assigned_to_max_tasks(worker))
    return {'tasks': tasks,
            'preventNewTasks': prevent_new_tasks,
            'reviewerStatus': worker_has_reviewer_status(worker)}


@json_view
@login_required
def new_task_assignment(request, task_type):
    new_tasks_status = {
        'entry_level': Task.Status.AWAITING_PROCESSING,
        'reviewer': Task.Status.PENDING_REVIEW
    }
    try:
        task_status = new_tasks_status[task_type]
    except KeyError:
        raise BadRequest('No such task type')

    worker = Worker.objects.get(user=request.user)
    try:
        task_assignment = get_new_task_assignment(worker, task_status)
    except WorkerCertificationError:
        raise BadRequest('No worker certificates')
    except NoTaskAvailable:
        raise BadRequest('No task')

    task = task_assignment.task
    return {'id': task.id,
            'step': task.step_slug,
            'project': task.project.workflow_slug,
            'detail': task.project.short_description}


@json_view
@login_required
def upload_image(request):
    upload_data = json.loads(request.body.decode())
    image_type = upload_data['image_type']
    image_data = base64.b64decode(upload_data['image_data'])
    prefix = upload_data.get('prefix') or ''
    if settings.PRODUCTION:
        prefix = os.path.join('production', prefix)
    else:
        prefix = os.path.join('development', prefix)
    return {'url': upload_editor_image(image_data, image_type, prefix)}


@json_view
@login_required
def task_assignment_information(request):
    try:
        worker = Worker.objects.get(user=request.user)
        return get_task_overview_for_worker(
            json.loads(request.body.decode())['task_id'],
            worker)
    except TaskAssignmentError as e:
        raise BadRequest(e)
    except Task.DoesNotExist as e:
        raise BadRequest(e)


@json_view
@login_required
def save_task_assignment(request):
    assignment_information = json.loads(request.body.decode())
    worker = Worker.objects.get(user=request.user)
    try:
        save_task(assignment_information['task_id'],
                  assignment_information['task_data'],
                  worker)
        return {}
    except Task.DoesNotExist:
        raise BadRequest('No task for given id')
    except TaskAssignmentError as e:
        raise BadRequest(e)


@json_view
@login_required
def submit_task_assignment(request):
    assignment_information = json.loads(request.body.decode())
    worker = Worker.objects.get(user=request.user)
    command_type = assignment_information['command_type']
    work_time_seconds = assignment_information['work_time_seconds']

    if command_type == 'accept':
        snapshot_type = TaskAssignment.SnapshotType.ACCEPT
    elif command_type == 'reject':
        snapshot_type = TaskAssignment.SnapshotType.REJECT
    elif command_type == 'submit':
        snapshot_type = TaskAssignment.SnapshotType.SUBMIT
    else:
        raise BadRequest('Illegal command')

    try:
        submit_task(assignment_information['task_id'],
                    assignment_information['task_data'],
                    snapshot_type,
                    worker,
                    work_time_seconds)
        return {}
    except TaskStatusError:
        raise BadRequest('Task already completed')
    except Task.DoesNotExist:
        raise BadRequest('No task for given id')
    except IllegalTaskSubmission as e:
        raise BadRequest(e)
    except TaskAssignmentError as e:
        raise BadRequest(e)


# A simple status endpoint for things like health checks, etc.
def status(request):
    return HttpResponse('OK')
