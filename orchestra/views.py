import base64
import json
import os
from collections import defaultdict

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.http import HttpResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.templatetags.static import static
from jsonview.decorators import json_view
from jsonview.exceptions import BadRequest
from registration.models import RegistrationProfile
from registration.views import RegistrationView
from rest_framework import serializers
from rest_framework import status as http_status

from orchestra import signals
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import TimerError
from orchestra.core.errors import WorkerCertificationError
from orchestra.core.errors import NoTaskAvailable
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import IllegalTaskSubmission
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.models import Step
from orchestra.project_api.serializers import TaskTimerSerializer
from orchestra.project_api.serializers import TimeEntrySerializer
from orchestra.utils.s3 import upload_editor_image
from orchestra.utils import time_tracking
from orchestra.utils.task_lifecycle import save_task
from orchestra.utils.task_lifecycle import submit_task
from orchestra.utils.task_lifecycle import tasks_assigned_to_worker
from orchestra.utils.task_lifecycle import get_new_task_assignment
from orchestra.utils.task_lifecycle import get_task_overview_for_worker
from orchestra.utils.task_lifecycle import worker_assigned_to_rejected_task
from orchestra.utils.task_lifecycle import worker_assigned_to_max_tasks
from orchestra.utils.task_lifecycle import worker_has_reviewer_status
from orchestra.utils.time_tracking import save_time_entry
from orchestra.utils.time_tracking import time_entries_for_worker

import logging

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
        'angular_directives': defaultdict(lambda: defaultdict(lambda: {}))}

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
            'step': task.step.slug,
            'project': task.project.workflow_version.slug,
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


@json_view
@login_required
def time_entries(request):
    worker = Worker.objects.get(user=request.user)
    try:
        if request.method == 'GET':
            return time_entries_for_worker(worker,
                                           task_id=request.GET.get('task-id'))
        elif request.method == 'POST':
            time_entry_data = json.loads(request.body.decode())
            if 'task_id' not in time_entry_data:
                raise BadRequest('Include task id in request data')
            task_id = time_entry_data.pop('task_id')
            return save_time_entry(worker, task_id, time_entry_data)
    except Task.DoesNotExist:
        raise BadRequest('No task for given id')
    except TaskAssignment.DoesNotExist:
        raise BadRequest('Worker is not assigned to this task id.')
    except (TaskStatusError, serializers.ValidationError) as e:
        raise BadRequest(e)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise e


@json_view
@login_required
def start_timer(request):
    worker = Worker.objects.get(user=request.user)
    try:
        if request.method == 'POST':
            time_entry_data = json.loads(request.body.decode())
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
        logger.error(e, exc_info=True)
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
        logger.error(e, exc_info=True)
        raise e


@json_view
@login_required
def get_timer(request):
    worker = Worker.objects.get(user=request.user)
    try:
        if request.method == 'GET':
            duration = time_tracking.get_timer_current_duration(worker)
            return str(duration)
    except Exception as e:
        logger.error(e, exc_info=True)
        raise e


# A simple status endpoint for things like health checks, etc.
def status(request):
    return HttpResponse('OK')


class OrchestraRegistrationView(RegistrationView):
    SEND_ACTIVATION_EMAIL = getattr(settings, 'SEND_ACTIVATION_EMAIL', True)
    success_url = 'registration_complete'

    def register(self, form):
        """
        Given a username, email address and password, register a new
        user account, which will initially be inactive.
        Along with the new ``User`` object, a new
        ``registration.models.RegistrationProfile`` will be created,
        tied to that ``User``, containing the activation key which
        will be used for this account.
        An email will be sent to the supplied email address; this
        email should contain an activation link. The email will be
        rendered using two templates. See the documentation for
        ``RegistrationProfile.send_activation_email()`` for
        information about these templates and the contexts provided to
        them.
        After the ``User`` and ``RegistrationProfile`` are created and
        the activation email is sent, the signal
        ``orchestra.signals.orchestra_user_registered`` will be sent,
        with the new ``User`` as the keyword argument ``user`` and the
        class of this backend as the sender.
        """
        site = get_current_site(self.request)

        if hasattr(form, 'save'):
            new_user_instance = form.save()
        else:
            new_user_instance = (UserModel().objects
                                 .create_user(**form.cleaned_data))

        new_user = RegistrationProfile.objects.create_inactive_user(
            new_user=new_user_instance,
            site=site,
            send_email=self.SEND_ACTIVATION_EMAIL,
            request=self.request,
        )

        # We send our own custom signal here so we don't conflict with anyone
        # using the django-registration project
        signals.orchestra_user_registered.send(sender=self.__class__,
                                               user=new_user,
                                               request=self.request)
        return new_user


def error_handler(request, error_code, context):
    context.update({
        'contact_us': settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL,
        'err_title': error_code,
    })
    return render(request,
                  'orchestra/error.html',
                  context=context,
                  status=error_code)


def bad_request(request):
    error_code = http_status.HTTP_400_BAD_REQUEST
    return error_handler(request, error_code, context={
        'page_title': '400 Bad Request',
    })


def permission_denied(request):
    error_code = http_status.HTTP_403_PERMISSION_DENIED
    return error_handler(request, error_code, context={
        'page_title': '403 Permission Denied',
    })


def page_not_found(request):
    error_code = http_status.HTTP_404_NOT_FOUND
    return error_handler(request, error_code, context={
        'page_title': '404 Page Not Found',
    })


def server_error(request):
    error_code = http_status.HTTP_500_INTERNAL_SERVER_ERROR
    return error_handler(request, error_code, context={
        'page_title': '500 Server Error',
    })
