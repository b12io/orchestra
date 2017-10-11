import base64
import json
import logging
import os
from collections import defaultdict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.csrf import requires_csrf_token
from django_filters import rest_framework as filters
from jsonview.decorators import json_view
from jsonview.exceptions import BadRequest
from rest_framework import status as http_status
from rest_framework import generics
from rest_framework import permissions

from orchestra.core.errors import IllegalTaskSubmission
from orchestra.core.errors import NoTaskAvailable
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import TimerError
from orchestra.core.errors import WorkerCertificationError
from orchestra.filters import TimeEntryFilter
from orchestra.models import Iteration
from orchestra.models import Step
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TimeEntry
from orchestra.models import Worker
from orchestra.project_api.serializers import TaskTimerSerializer
from orchestra.project_api.serializers import TimeEntrySerializer
from orchestra.utils import time_tracking
from orchestra.utils.load_json import load_encoded_json
from orchestra.utils.s3 import upload_editor_image
from orchestra.utils.task_lifecycle import get_new_task_assignment
from orchestra.utils.task_lifecycle import get_task_overview_for_worker
from orchestra.utils.task_lifecycle import save_task
from orchestra.utils.task_lifecycle import submit_task
from orchestra.utils.task_lifecycle import tasks_assigned_to_worker
from orchestra.utils.task_lifecycle import worker_assigned_to_max_tasks
from orchestra.utils.task_lifecycle import worker_assigned_to_rejected_task
from orchestra.utils.task_lifecycle import worker_has_reviewer_status
from orchestra.utils.view_helpers import IsAssociatedWorker

logger = logging.getLogger(__name__)
UserModel = get_user_model()


# NOTE(joshblum): whitenoise is a bit over eager and tries to replace our
# {{js/css}} with a static resource, so we don't put these script tags on the
# page
def _get_script_tag(script):
    return '<script src="{}" type="text/javascript"></script>'.format(script)


def _get_style_tag(style):
    return '<link href="{}" rel="stylesheet">'.format(style)


@login_required
def index(request):
    javascript_includes = []
    stylesheet_includes = []
    orchestra_arguments = {
        'angular_modules': [],
        'angular_directives': defaultdict(lambda: defaultdict(lambda: {})),
        'enable_new_task_buttons': settings.ORCHESTRA_ENABLE_NEW_TASK_BUTTONS,
    }

    for step in Step.objects.filter(is_human=True):
        # Preserve js and stylesheet order while removing duplicates
        for js in step.user_interface.get('javascript_includes', []):
            static_js = _get_script_tag(static(js))
            if static_js not in javascript_includes:
                javascript_includes.append(static_js)
        for style in step.user_interface.get('stylesheet_includes', []):
            static_style = _get_style_tag(static(style))
            if static_style not in stylesheet_includes:
                stylesheet_includes.append(static_style)

        if step.user_interface.get('angular_module'):
            orchestra_arguments['angular_modules'].append(
                step.user_interface['angular_module'])

        if step.user_interface.get('angular_directive'):
            orchestra_arguments['angular_directives'][
                step.workflow_version.workflow.slug][
                    step.workflow_version.slug][step.slug] = (
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
            'preventNew': prevent_new_tasks,
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
    return {
        'id': task.id,
        'assignment_id': task_assignment.id,
        'step': task.step.slug,
        'project': task.project.workflow_version.slug,
        'detail': task.project.short_description
    }


@json_view
@login_required
def upload_image(request):
    upload_data = load_encoded_json(request.body)
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
            load_encoded_json(request.body)['task_id'],
            worker)
    except TaskAssignmentError as e:
        raise BadRequest(e)
    except Task.DoesNotExist as e:
        raise BadRequest(e)


@json_view
@login_required
def save_task_assignment(request):
    assignment_information = load_encoded_json(request.body)
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
    assignment_information = load_encoded_json(request.body)
    worker = Worker.objects.get(user=request.user)
    command_type = assignment_information['command_type']

    if command_type in ('submit', 'accept'):
        iteration_status = Iteration.Status.REQUESTED_REVIEW
    elif command_type == 'reject':
        iteration_status = Iteration.Status.PROVIDED_REVIEW
    else:
        raise BadRequest('Illegal command')

    try:
        submit_task(assignment_information['task_id'],
                    assignment_information['task_data'],
                    iteration_status,
                    worker)
        return {}
    except TaskStatusError:
        raise BadRequest('Task already completed')
    except Task.DoesNotExist:
        raise BadRequest('No task for given id')
    except IllegalTaskSubmission as e:
        raise BadRequest(e)
    except TaskAssignmentError as e:
        raise BadRequest(e)


@json_view
@login_required
def start_timer(request):
    worker = Worker.objects.get(user=request.user)
    try:
        if request.method == 'POST':
            time_entry_data = load_encoded_json(request.body)
            assignment_id = None
            if 'assignment' in time_entry_data:
                assignment_id = time_entry_data['assignment']
            timer = time_tracking.start_timer(worker,
                                              assignment_id=assignment_id)
            serializer = TaskTimerSerializer(timer)
            return serializer.data
    except TaskAssignment.DoesNotExist:
        raise BadRequest('Worker is not assigned to this task id.')
    except TimerError as e:
        raise BadRequest(e)
    except Exception as e:
        logger.exception(e)
        raise e


@json_view
@login_required
def stop_timer(request):
    worker = Worker.objects.get(user=request.user)
    try:
        if request.method == 'POST':
            time_entry = time_tracking.stop_timer(worker)
            serializer = TimeEntrySerializer(time_entry)
            return serializer.data
    except TimerError as e:
        raise BadRequest(e)
    except Exception as e:
        logger.exception(e)
        raise e


@json_view
@login_required
def get_timer(request):
    worker = Worker.objects.get(user=request.user)
    try:
        if request.method == 'GET':
            timer = time_tracking.get_timer_object(worker)
            time_worked = time_tracking.get_timer_current_duration(worker)
            data = TaskTimerSerializer(timer).data
            if time_worked:
                data['time_worked'] = str(time_worked)
            return data
    except Exception as e:
        logger.error(e, exc_info=True)
        raise e


@json_view
@login_required
def update_timer(request):
    worker = Worker.objects.get(user=request.user)
    try:
        if request.method == 'POST':
            data = load_encoded_json(request.body)
            time_tracking.update_timer(
                worker, data.get('description'), data.get('assignment'))
    except Exception as e:
        logger.error(e, exc_info=True)
        raise e


# A simple status endpoint for things like health checks, etc.
def status(request):
    return HttpResponse('OK')


def error_handler(request, error_code, context):
    context.update({
        'contact_us': settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL,
        'err_title': error_code,
    })
    return render(request,
                  'orchestra/error.html',
                  context=context,
                  status=error_code)


@requires_csrf_token
def bad_request(request):
    error_code = http_status.HTTP_400_BAD_REQUEST
    return error_handler(request, error_code, context={
        'page_title': '400 Bad Request',
    })


@requires_csrf_token
def forbidden(request):
    error_code = http_status.HTTP_403_FORBIDDEN
    return error_handler(request, error_code, context={
        'page_title': '403 Forbidden',
    })


@requires_csrf_token
def not_found(request):
    error_code = http_status.HTTP_404_NOT_FOUND
    return error_handler(request, error_code, context={
        'page_title': '404 Not Found',
    })


@requires_csrf_token
def internal_server_error(request):
    error_code = http_status.HTTP_500_INTERNAL_SERVER_ERROR
    return error_handler(request, error_code, context={
        'page_title': '500 Internal Server Error',
    })


class TimeEntryList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = TimeEntrySerializer
    filter_backends = (filters.DjangoFilterBackend,)
    filter_class = TimeEntryFilter

    def get_queryset(self):
        """
        Return time entries for current user, filtering on assignment id
        if provided.
        """
        # TODO(lydia): Add time filter to queryset.
        worker = Worker.objects.get(user=self.request.user)
        queryset = TimeEntry.objects.filter(worker=worker)
        assignment_id = self.request.query_params.get('assignment', None)
        if assignment_id is not None:
            queryset = queryset.filter(assignment__id=assignment_id)
        return queryset

    def perform_create(self, serializer):
        """
        Overwrite perform_create so that user can only create time entries
        for him or herself.
        """
        # TODO(lydia): Is there a way to prevent workers from creating
        # time entries for completed TaskAssignments?
        worker = Worker.objects.get(user=self.request.user)
        serializer.save(worker=worker)


class TimeEntryDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated, IsAssociatedWorker)
    queryset = TimeEntry.objects.all()
    serializer_class = TimeEntrySerializer
