import logging
import random
from pydoc import locate

from django.conf import settings
from django.db import connection
from django.db import transaction
from django.db.models import Case
from django.db.models import When
from django.db.models import Q
from django.db.models import Value
from django.db.models import IntegerField
from django.utils import timezone


from orchestra.communication.slack import add_worker_to_project_team
from orchestra.communication.slack import archive_project_slack_group
from orchestra.communication.utils import mark_worker_as_winner
from orchestra.core.errors import AssignmentPolicyError
from orchestra.core.errors import CreationPolicyError
from orchestra.core.errors import IllegalTaskSubmission
from orchestra.core.errors import ModelSaveError
from orchestra.core.errors import NoTaskAvailable
from orchestra.core.errors import ReviewPolicyError
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import TaskDependencyError
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import ProjectStatusError
from orchestra.core.errors import WorkerCertificationError
from orchestra.models import Iteration
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.todos.api import add_todolist_template
from orchestra.utils.notifications import notify_status_change
from orchestra.utils.notifications import notify_project_status_change
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import current_assignment
from orchestra.utils.task_properties import get_latest_iteration

logger = logging.getLogger(__name__)


class AssignmentPolicyType(object):
    ENTRY_LEVEL = 'entry_level'
    REVIEWER = 'reviewer'


def worker_assigned_to_max_tasks(worker):
    """
    Check whether worker is assigned to the maximum number of tasks.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.

    Returns:
        assigned_to_max_tasks (bool):
            True if worker is assigned to the maximum number of tasks.
    """
    assigned_to_max_tasks = False
    return assigned_to_max_tasks


def worker_assigned_to_rejected_task(worker):
    """
    Check whether worker is assigned to a task that has been rejected.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.

    Returns:
        assigned_to_rejected_task (bool):
            True if worker is assigned to a task that has been rejected.
    """
    assigned_to_rejected_task = (
        TaskAssignment.objects
                      .filter(worker=worker,
                              status=TaskAssignment.Status.PROCESSING,
                              task__status=Task.Status.POST_REVIEW_PROCESSING)
                      .exists()
    )
    return assigned_to_rejected_task


def worker_has_reviewer_status(worker,
                               task_class=WorkerCertification.TaskClass.REAL):
    """
    Check whether worker is a reviewer for any certification for a
    given task class.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.
        task_class (orchestra.models.WorkerCertification.TaskClass):
            The specified task class.

    Returns:
        has_reviwer_status (bool):
            True if worker is a reviewer for any certification for a
            given task class.
    """
    has_reviwer_status = (
        WorkerCertification.objects
                           .filter(worker=worker,
                                   role=WorkerCertification.Role.REVIEWER,
                                   task_class=task_class)
                           .exists())
    return has_reviwer_status


def is_worker_certified_for_task(
        worker, task, role, task_class=WorkerCertification.TaskClass.REAL,
        require_staffbot_enabled=False):
    """
    Check whether worker is certified for a given task, role, and task
    class.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.
        task (orchestra.models.Task):
            The specified task object.
        task_class (orchestra.models.WorkerCertification.TaskClass):
            The specified task class.
        require_staffbot_enabled (bool):
            Whether to require that the `staffbot_enabled` flag be `True`.

    Returns:
        certified_for_task (bool):
            True if worker is certified for a given task, role, and task
            class.
    """
    step = task.step

    worker_certifications = (
        WorkerCertification
        .objects
        .filter(worker=worker,
                role=role,
                task_class=task_class,
                certification__in=step.required_certifications.all()))
    if require_staffbot_enabled:
        worker_certifications = worker_certifications.filter(
            staffbot_enabled=True)
    certified_for_task = (
        step.required_certifications.count() == worker_certifications.count())
    return certified_for_task


def get_role_from_counter(role_counter):
    if role_counter == 0:
        return WorkerCertification.Role.ENTRY_LEVEL
    return WorkerCertification.Role.REVIEWER


def role_counter_required_for_new_task(task):
    """
    Given a task find a level of expert that is required
    to be assigned for task.
    """
    if task.status not in [Task.Status.AWAITING_PROCESSING,
                           Task.Status.PENDING_REVIEW]:
        raise TaskAssignmentError('Status incompatible with new assignment')
    elif (task.status == Task.Status.AWAITING_PROCESSING and
          task.assignments.filter(assignment_counter=0).exists()):
        raise TaskAssignmentError('Task is in incorrect state')
    assignments_count = task.assignments.count()
    for assignment_counter in range(assignments_count):
        task_assignment = (task.assignments
                           .filter(assignment_counter=assignment_counter))
        if not task_assignment.exists():
            return assignment_counter
    return assignments_count


def role_required_for_new_task(task):
    roles = {
        Task.Status.AWAITING_PROCESSING: WorkerCertification.Role.ENTRY_LEVEL,
        Task.Status.PENDING_REVIEW: WorkerCertification.Role.REVIEWER
    }

    required_role = roles.get(task.status)
    if required_role is None:
        raise TaskAssignmentError('Status incompatible with new assignment')
    return required_role


@transaction.atomic
def assign_task(worker_id, task_id, staffing_request_inquiry=None):
    """
    Return a given task after assigning or reassigning it to the specified
    worker.

    Args:
        worker_id (int):
            The ID of the worker to be assigned.
        task_id (int):
            The ID of the task to be assigned.

    Returns:
        task (orchestra.models.Task):
            The newly assigned task.

    Raises:
        orchestra.core.errors.TaskAssignmentError:
            The specified worker is already assigned to the given task
            or the task status is not compatible with new assignment.
        orchestra.core.errors.WorkerCertificationError:
            The specified worker is not certified for the given task.
    """
    worker = Worker.objects.get(id=worker_id)
    task = Task.objects.get(id=task_id)
    required_role = role_required_for_new_task(task)
    required_role_counter = role_counter_required_for_new_task(task)

    assignment = current_assignment(task)
    if not is_worker_certified_for_task(worker, task, required_role):
        raise WorkerCertificationError('Worker not certified for this task.')
    if task.is_worker_assigned(worker):
        raise TaskAssignmentError('Worker already assigned to this task.')

    assignment_counter = task.assignments.count()
    in_progress_task_data = {}

    if assignment:
        # In-progress task data is the latest
        # submission by a previous worker
        in_progress_task_data = assignment.in_progress_task_data

    previous_status = task.status
    if previous_status == Task.Status.AWAITING_PROCESSING:
        task.status = Task.Status.PROCESSING
    elif previous_status == Task.Status.PENDING_REVIEW:
        task.status = Task.Status.REVIEWING
    task.save()
    assignment = (
        TaskAssignment.objects
        .create(worker=worker,
                task=task,
                status=TaskAssignment.Status.PROCESSING,
                assignment_counter=assignment_counter,
                in_progress_task_data=in_progress_task_data))

    Iteration.objects.create(
        assignment=assignment,
        start_datetime=assignment.start_datetime)

    if settings.PRODUCTION or settings.STAGING:
        add_worker_to_project_team(worker, task.project)
    notify_status_change(task, previous_status)
    mark_worker_as_winner(worker, task, required_role_counter,
                          staffing_request_inquiry)
    return task


@transaction.atomic
def reassign_assignment(worker_id, assignment_id,
                        staffing_request_inquiry=None):
    """
    Return a given assignment after reassigning it to the specified
    worker.

    Args:
        worker_id (int):
            The ID of the worker to be assigned.
        assignment_id (int):
            The ID of the assignment to be assigned.

    Returns:
        assignment (orchestra.models.TaskAssignment):
            The newly assigned assignment.

    Raises:
        orchestra.core.errors.TaskAssignmentError:
            The specified worker is already assigned to the given task.
        orchestra.core.errors.WorkerCertificationError:
            The specified worker is not certified for the given assignment.
    """
    worker = Worker.objects.get(id=worker_id)
    assignment = TaskAssignment.objects.get(id=assignment_id)
    if assignment.assignment_counter > 0:
        role = WorkerCertification.Role.REVIEWER
    else:
        role = WorkerCertification.Role.ENTRY_LEVEL

    if not is_worker_certified_for_task(worker, assignment.task, role):
        raise WorkerCertificationError(
            'Worker not certified for this assignment.')
    if assignment.task.is_worker_assigned(worker):
        raise TaskAssignmentError('Worker already assigned to this task.')

    assignment.worker = worker
    assignment.save()

    mark_worker_as_winner(worker, assignment.task,
                          assignment.assignment_counter,
                          staffing_request_inquiry)
    add_worker_to_project_team(worker, assignment.task.project)
    return assignment


@transaction.atomic
def complete_and_skip_task(task_id):
    """
    Submits a task on behalf of the worker working on it. If the task
    isn't assigned to a worker, marks it and its assignments as
    complete and creates subsequent tasks.

    Args:
        task_id (int):
            The ID of the task to be marked as complete and skipped.

    Returns:
        task (orchestra.models.Task):
            The completed and skipped task.

    """
    task = Task.objects.get(id=task_id)
    assignment = current_assignment(task)
    if assignment and assignment.worker:
        if assignment.status != TaskAssignment.Status.PROCESSING:
            return task
        task_data = assignment.in_progress_task_data or {}
        task_data.update(_orchestra_internal={'complete_and_skip_task': True})
        submit_task(
            task_id, task_data,
            Iteration.Status.REQUESTED_REVIEW, assignment.worker)
    else:
        task.status = Task.Status.COMPLETE
        task.save()
        for assignment in task.assignments.all():
            assignment.status = TaskAssignment.Status.SUBMITTED
            assignment.save()
    return task


def get_task_details(task_id):
    """
    Return various information about the specified task.

    Args:
        task_id (int): The ID of the desired task.

    Returns:
        task_details (dict): Information about the specified task.
    """
    task = Task.objects.select_related('step__workflow_version__workflow').get(
        id=task_id)
    step = task.step
    project = task.project
    workflow_version = step.workflow_version
    workflow = workflow_version.workflow
    prerequisites = get_previously_completed_task_data(step, project)

    task_details = {
        'workflow': {
            'slug': workflow.slug,
            'name': workflow.name,
        },
        'workflow_version': {
            'slug': workflow_version.slug,
            'name': workflow_version.name,
        },
        'step': {
            'slug': step.slug,
            'name': step.name
        },
        'task_id': task.id,
        'project': {
            'id': project.id,
            'details': project.short_description,
            'team_messages_url': project.team_messages_url,
            'project_data': project.project_data,
            'status': dict(Project.STATUS_CHOICES)[project.status]
        },
        'prerequisites': prerequisites
    }
    return task_details


def get_task_assignment_details(task_assignment):
    """
    Return various information about the specified task assignment.

    Args:
        task_assignment (orchestra.models.TaskAssignment):
            The specified task assignment.

    Returns:
        task_assignment_details (dict):
            Information about the specified task assignment.
    """
    reviewer_task_assignment = (
        TaskAssignment.objects.filter(
            task=task_assignment.task)
        .order_by('-assignment_counter')[0])

    worker = task_assignment.worker
    worker_info = {attr: getattr(getattr(worker, 'user', None), attr, None)
                   for attr in ('username', 'first_name', 'last_name')}

    return {
        'assignment_id': task_assignment.id,
        'task': {
            'data': task_assignment.in_progress_task_data,
            'status': (dict(Task.STATUS_CHOICES)
                       [task_assignment.task.status])
        },
        'worker': worker_info,
        'status': (dict(TaskAssignment.STATUS_CHOICES)
                   [task_assignment.status]),
        'is_reviewer': (
            task_assignment.id == reviewer_task_assignment.id and
            task_assignment.assignment_counter > 0),
        'is_read_only': (
            task_assignment.status != TaskAssignment.Status.PROCESSING),
    }


def get_task_overview_for_worker(task_id, worker):
    """
    Get information about `task` and its assignment for `worker`.

    Args:
        task_id (int):
            The ID of the desired task object.
        worker (orchestra.models.Worker):
            The specified worker object.

    Returns:
        task_assignment_details (dict):
            Information about `task` and its assignment for `worker`.
    """
    task = Task.objects.get(id=task_id)
    task_details = get_task_details(task_id)
    task_details['is_project_admin'] = worker.is_project_admin()

    if task.is_worker_assigned(worker):
        task_assignment = TaskAssignment.objects.get(worker=worker, task=task)
    elif worker.is_project_admin():
        task_assignment = assignment_history(task).last()
        task_details['is_read_only'] = True
    else:
        raise TaskAssignmentError('Worker is not associated with task')

    task_assignment_details = get_task_assignment_details(task_assignment)
    task_assignment_details.update(task_details)
    return task_assignment_details


def tasks_assigned_to_worker(worker):
    """
    Get all the tasks associated with `worker`.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.

    Returns:
        tasks_assigned (dict):
            A dict with information about the worker's tasks, used in
            displaying the Orchestra dashboard.
    """
    valid_task_assignments = TaskAssignment.objects.exclude(
        task__status=Task.Status.ABORTED)

    # get all active task assignments for a user
    active_task_assignments = (
        valid_task_assignments
        .filter(
            worker=worker,
            status=TaskAssignment.Status.PROCESSING)
        .exclude(
            task__project__status__in=[Project.Status.PAUSED,
                                       Project.Status.COMPLETED])
        .order_by('-task__project__priority',
                  'task__project__start_datetime'))

    inactive_task_assignments = (
        valid_task_assignments
        .filter(
            worker=worker,
            status=TaskAssignment.Status.SUBMITTED
        )
        .exclude(
            task__status=Task.Status.COMPLETE)
        .exclude(
            task__project__status__in=[Project.Status.PAUSED,
                                       Project.Status.COMPLETED])
        .order_by('-task__project__priority',
                  'task__project__start_datetime'))

    inactive_processing_task_assignments = []
    inactive_review_task_assignments = []
    for task_assignment in inactive_task_assignments:
        if (
                valid_task_assignments
                .filter(
                    status=TaskAssignment.Status.PROCESSING,
                    task__id=task_assignment.task.id,
                    assignment_counter__lt=task_assignment.assignment_counter)
                .exists()):
            inactive_processing_task_assignments.append(task_assignment)
        else:
            inactive_review_task_assignments.append(task_assignment)

    # TODO(marcua): Do a better job of paginating than cutting off to the most
    # recent 200 tasks.
    complete_task_assignments = (
        valid_task_assignments
        .filter(Q(worker=worker) &
                (Q(task__status=Task.Status.COMPLETE) |
                 Q(task__project__status=Project.Status.COMPLETED)))
        .order_by('-task__project__priority',
                  '-task__project__start_datetime')[:200])

    paused_task_assignments = (
        valid_task_assignments
        .filter(
            worker=worker,
            status=TaskAssignment.Status.PROCESSING,
            task__project__status=Project.Status.PAUSED)
        .order_by('-task__project__priority',
                  'task__project__start_datetime'))

    task_assignments_overview = {
        'returned': (
            active_task_assignments
            .filter(task__status=Task.Status.POST_REVIEW_PROCESSING)),
        'in_progress': (
            active_task_assignments
            .exclude(task__status=Task.Status.POST_REVIEW_PROCESSING)),
        'pending_review': inactive_review_task_assignments,
        'pending_processing': inactive_processing_task_assignments,
        'paused': paused_task_assignments,
        'complete': complete_task_assignments}

    tasks_assigned = []
    time_now = timezone.now()
    for state, task_assignments in iter(task_assignments_overview.items()):
        for task_assignment in task_assignments:
            step = task_assignment.task.step
            workflow_version = step.workflow_version
            next_todo_title = None
            next_todo_dict = {}
            should_be_active = False
            if state in ('returned', 'in_progress'):
                next_todo = (
                    task_assignment.task.todos
                    .filter(
                        completed=False,
                        template=None
                    ).annotate(
                        todo_order=Case(
                            When(
                                start_by_datetime__gt=time_now,
                                then=Value(3)),
                            When(
                                due_datetime=None,
                                then=Value(2)),
                            default=Value(1),
                            output_field=IntegerField()
                        )
                    )
                    .order_by(
                        'todo_order',
                        'due_datetime',
                        'start_by_datetime',
                        '-created_at'
                    )
                    .first())

                if next_todo:
                    next_todo_title = next_todo.title
                    start_str = (
                        next_todo.start_by_datetime.strftime(
                            '%Y-%m-%dT%H:%M:%SZ'
                        ) if next_todo.start_by_datetime else ''
                    )
                    due_str = (
                        next_todo.due_datetime.strftime(
                            '%Y-%m-%dT%H:%M:%SZ'
                        ) if next_todo.due_datetime else ''
                    )
                    next_todo_dict = {
                        'title': next_todo.title,
                        'start_by_datetime': start_str,
                        'due_datetime': due_str
                    }
                num_non_template_todos = (
                    task_assignment.task.todos
                    .filter(template=None).count())
                # If a task has no todos (complete or incomplete)
                # assigned to it, then by default the task would be
                # marked as pending. When a task is first created and
                # picked up by a worker, it will thus be in pending
                # state, which is confusing behavior. We thus treat a
                # task with zero todos as active. After a task has one
                # or more todos assigned to it, its active/pending
                # state is determined by the presence of incomplete
                # todos.
                task_started = (
                    next_todo_title is not None
                    and (
                        next_todo.start_by_datetime is None
                        or next_todo.start_by_datetime <= time_now
                    )
                )
                should_be_active = (
                    (num_non_template_todos == 0)
                    or task_started)
            tasks_assigned.append({
                'id': task_assignment.task.id,
                'assignment_id': task_assignment.id,
                'step': step.name,
                'project': workflow_version.name,
                'detail': task_assignment.task.project.short_description,
                'priority': task_assignment.task.project.priority,
                'state': state,
                'assignment_start_datetime': task_assignment.start_datetime,
                'next_todo_dict': next_todo_dict,
                'should_be_active': should_be_active,
                'tags': task_assignment.task.tags.get('tags', [])
            })
    return tasks_assigned


def _is_review_needed(task):
    """
    Determine if `task` will be reviewed according to its step policy.

    Args:
        task (orchestra.models.Task):
            The specified task object.

    Returns:
        review_needed (bool):
            True if review is determined to be needed according to the
            task's step policy.

    Raises:
        orchestra.core.errors.ReviewPolicyError:
            The specified review policy type is not supported.
    """
    policy_dict = task.step.review_policy
    policy = policy_dict.get('policy')
    sample_rate = policy_dict.get('rate')
    max_reviews = policy_dict.get('max_reviews')

    if (policy == 'sampled_review' and
            sample_rate is not None and
            max_reviews is not None):
        task_assignment_count = task.assignments.all().count()
        if max_reviews <= task_assignment_count - 1:
            return False
        return random.random() < sample_rate
    elif policy == 'no_review':
        return False
    else:
        raise ReviewPolicyError('Review policy incorrectly specified.')


def get_next_task_status(task, iteration_status):
    """
    Given current task status and snapshot type provide new task status.
    If the second level reviewer rejects a task then initial reviewer
    cannot reject it further down, but must fix and submit the task.

    Args:
        task (orchestra.models.Task):
            The specified task object.
        iteration_status (orchestra.models.Iteration.Status):
            The action taken upon task submission (i.e., REQUESTED_REVIEW
            or PROVIDED_REVIEW).

    Returns:
        next_status (orchestra.models.Task.Status):
            The next status of `task`, once the `iteration_status` action
            has been completed.

    Raises:
        orchestra.core.errors.IllegalTaskSubmission:
            The `iteration_status` action cannot be taken for the task in
            its current status.
    """
    # Task with one of these statuses cannot be submitted
    illegal_statuses = [Task.Status.AWAITING_PROCESSING,
                        Task.Status.PENDING_REVIEW,
                        Task.Status.COMPLETE]

    if task.status in illegal_statuses:
        raise IllegalTaskSubmission('Task has illegal status for submit.')
    elif iteration_status == Iteration.Status.REQUESTED_REVIEW:
        if task.status in (Task.Status.PROCESSING, Task.Status.REVIEWING):
            if _is_review_needed(task):
                return Task.Status.PENDING_REVIEW
            else:
                return Task.Status.COMPLETE
        elif task.status == Task.Status.POST_REVIEW_PROCESSING:
            return Task.Status.REVIEWING
        else:
            raise IllegalTaskSubmission('Task not in submittable state.')
    elif iteration_status == Iteration.Status.PROVIDED_REVIEW:
        if task.status == Task.Status.REVIEWING:
            return Task.Status.POST_REVIEW_PROCESSING
        else:
            raise IllegalTaskSubmission('Task not in rejectable state.')


def check_worker_allowed_new_assignment(worker):
    """
    Check if the worker can be assigned to a new task.

    Args:
        worker (orchestra.models.Worker):
            The worker submitting the task.
        task_status (orchestra.models.Task.Status):
            The status of the desired new task assignment.

    Returns:
        allowed_new_assignment (bool):
            True if the worker can be assigned to a new task.

    Raises:
        orchestra.core.errors.TaskAssignmentError:
            Worker has pending reviewer feedback or is assigned to the
            maximum number of tasks.
        orchestra.core.errors.TaskStatusError:
            New task assignment is not permitted for the given status.
    """
    if (worker_assigned_to_rejected_task(worker) and
            settings.ORCHESTRA_ENFORCE_NO_NEW_TASKS_DURING_REVIEW):
        raise TaskAssignmentError('Worker has pending reviewer feedback that '
                                  'must be addressed.')
    elif worker_assigned_to_max_tasks(worker):
        raise TaskAssignmentError('Worker assigned to max number of tasks.')


def assert_new_task_status_valid(task_status):
    valid_statuses = [Task.Status.AWAITING_PROCESSING,
                      Task.Status.PENDING_REVIEW]
    if task_status not in valid_statuses:
        raise TaskStatusError('Invalid status for new task assignment.')


def get_new_task_assignment(worker, task_status):
    """
    Check if new task assignment is available for the provided worker
    and task status; if so, assign the task to the worker and return the
    assignment.

    Args:
        worker (orchestra.models.Worker):
            The worker submitting the task.
        task_status (orchestra.models.Task.Status):
            The status of the desired new task assignment.

    Returns:
        assignment (orchestra.models.TaskAssignment):
            The newly created task assignment.

    Raises:
        orchestra.core.errors.WorkerCertificationError:
            No human tasks are available for the given task status
            except those for which the worker is not certified.
        orchestra.core.errors.NoTaskAvailable:
            No human tasks are available for the given task status.
    """
    assert_new_task_status_valid(task_status)
    check_worker_allowed_new_assignment(worker)

    tasks = (Task.objects
             .filter(status=task_status)
             .exclude(assignments__worker=worker)
             .order_by('-project__priority')
             .order_by('project__start_datetime'))

    certification_error = False
    for task in tasks:
        try:
            task = assign_task(worker.id, task.id)
            return current_assignment(task)
        except WorkerCertificationError:
            certification_error = True
        except ModelSaveError:
            # Machine task cannot have human worker; treat machine tasks as if
            # they do not exist
            pass

    if certification_error:
        raise WorkerCertificationError
    else:
        raise NoTaskAvailable('No task available for {}'.format(worker))


@transaction.atomic
def save_task(task_id, task_data, worker):
    """
    Save the latest data to the database for a task assignment,
    overwriting previously saved data.

    Args:
        task_id (int):
            The ID of the task to save.
        task_data (str):
            A JSON blob of task data to commit to the database.
        worker (orchestra.models.Worker):
            The worker saving the task.

    Returns:
        None

    Raises:
        orchestra.core.errors.TaskAssignmentError:
            The provided worker is not assigned to the given task or the
            assignment is in a non-processing state.
    """
    task = Task.objects.get(id=task_id)
    if not task.is_worker_assigned(worker):
        raise TaskAssignmentError('Worker is not associated with task')

    # Use select_for_update to prevent concurrency issues with submit_task.
    # See https://github.com/b12io/orchestra/issues/2.
    assignment = (TaskAssignment.objects.select_for_update()
                                .get(task=task, worker=worker))

    if assignment.status != TaskAssignment.Status.PROCESSING:
        raise TaskAssignmentError('Worker is not allowed to save')

    assignment.in_progress_task_data = task_data
    assignment.save()


def _are_desired_steps_completed_on_project(desired_steps,
                                            project=None,
                                            completed_tasks=None):
    """
    Determines if `desired_steps` have already been completed on
    `project`. Either `project` or `completed_tasks` will be passed in,
    since the caller sometimes has one but not the other.

    Args:
        desired_steps (django.db.models.QuerySet):
            A queryset of orchestra.models.Step objects to check for
            completion.
        project (orchestra.models.Project):
            The project to check for desired step completion,
            optionally passed in instead of a list of completed tasks.
        completed_tasks (django.db.models.QuerySet):
            A queryset of orchestra.models.Task to check for desired step
            completion, optionally passed in instead of a project.

    Returns:
        desired_steps_completed (bool):
            True if the desired steps have been completed for the given
            project or list of tasks.

    Raises:
        Exception: Either project or completed_tasks must be provided.
    """
    if completed_tasks is None:
        if project is None:
            raise Exception('Must provide either project or completed_tasks')
        completed_tasks = Task.objects.filter(status=Task.Status.COMPLETE,
                                              project=project)
    completed_step_slugs = set(completed_tasks.values_list('step__slug',
                                                           flat=True))
    desired_step_slugs = set(desired_steps.values_list('slug', flat=True))
    return not (desired_step_slugs - completed_step_slugs)


@transaction.atomic
def submit_task(task_id, task_data, iteration_status, worker):
    """
    Returns a dict mapping task prerequisites onto their
    latest task assignment information.  The dict is of the form:
    {'previous-slug': {task_assignment_data}, ...}

    Args:
        task_id (int):
            The ID of the task to submit.
        task_data (str):
            A JSON blob of task data to submit.
        iteration_status (orchestra.models.Iteration.Status):
            The action taken upon task submission (i.e., REQUESTED_REVIEW
            or PROVIDED_REVIEW).
        worker (orchestra.models.Worker):
            The worker submitting the task.

    Returns:
        task (orchestra.models.Task):
            The modified task object.

    Raises:
        orchestra.core.errors.IllegalTaskSubmission:
            Submission prerequisites for the task are incomplete or the
            assignment is in a non-processing state.
        orchestra.core.errors.TaskAssignmentError:
            Worker belongs to more than one assignment for the given
            task.
        orchestra.core.errors.TaskStatusError:
            Task has already been completed.
    """
    submit_datetime = timezone.now()

    task = Task.objects.select_related('step', 'project').get(id=task_id)
    step = task.step
    if not _are_desired_steps_completed_on_project(step.submission_depends_on,
                                                   project=task.project):
        raise IllegalTaskSubmission('Submission prerequisites are not '
                                    'complete.')

    if task.status == Task.Status.COMPLETE:
        raise TaskStatusError('Task already completed')

    # Use select_for_update to prevent concurrency issues with save_task.
    # See https://github.com/b12io/orchestra/issues/2.
    assignments = (TaskAssignment.objects.select_for_update()
                                 .filter(worker=worker, task=task))

    # Worker can belong to only one assignment for a given task.
    if not assignments.count() == 1:
        raise TaskAssignmentError(
            'Task assignment with worker is in broken state.')

    assignment = assignments[0]

    if assignment.status != TaskAssignment.Status.PROCESSING:
        raise IllegalTaskSubmission('Worker is not allowed to submit')

    next_status = get_next_task_status(task, iteration_status)

    assignment.in_progress_task_data = task_data

    # Submit latest iteration
    latest_iteration = get_latest_iteration(assignment)
    latest_iteration.status = iteration_status
    latest_iteration.submitted_data = assignment.in_progress_task_data
    latest_iteration.end_datetime = submit_datetime
    latest_iteration.save()

    assignment.status = TaskAssignment.Status.SUBMITTED
    assignment.save()
    previous_status = task.status
    task.status = next_status
    task.save()

    if task.status == Task.Status.PENDING_REVIEW:
        # Check the assignment policy to try to assign a reviewer automatically
        task = _preassign_workers(task, AssignmentPolicyType.REVIEWER)
    elif task.status == Task.Status.REVIEWING:
        update_related_assignment_status(task,
                                         assignment.assignment_counter + 1,
                                         assignment.in_progress_task_data,
                                         submit_datetime)
    elif task.status == Task.Status.POST_REVIEW_PROCESSING:
        update_related_assignment_status(task,
                                         assignment.assignment_counter - 1,
                                         assignment.in_progress_task_data,
                                         submit_datetime)
    elif task.status == Task.Status.COMPLETE:
        create_subsequent_tasks(task.project)

    notify_status_change(task, previous_status)
    return task


def get_previously_completed_task_data(step, project):
    """
    Returns a dict mapping task prerequisites onto their
    latest task assignment information.  The dict is of the form:
    {'previous-slug': {latest_assignment_data}, ...}

    Args:
        step (orchestra.models.Step): The specified step object.
        project (orchestra.models.Project): The specified project object.
    Returns:
        prerequisites (dict):
            A dict mapping task prerequisites onto their latest task
            assignment information.
    """
    # Find all prerequisite steps in graph
    to_visit = list(step.creation_depends_on.all())
    prerequisite_steps = set(to_visit)
    while to_visit:
        current_step = to_visit.pop()
        for step in current_step.creation_depends_on.all():
            if step not in prerequisite_steps:
                to_visit.append(step)
                prerequisite_steps.add(step)

    prerequisite_data = {}
    for step in prerequisite_steps:
        required_task = Task.objects.get(step=step, project=project)

        if required_task.status != Task.Status.COMPLETE:
            raise TaskDependencyError('Task depenency is not satisfied')
        assignment = assignment_history(required_task).last()
        prerequisite_data[step.slug] = assignment.in_progress_task_data
    return prerequisite_data


def update_related_assignment_status(task, assignment_counter, data,
                                     submit_datetime):
    """
    Copy data to a specified task assignment and mark it as processing.

    Args:
        task (orchestra.models.Task):
            The task whose assignments will be updated.
        assignment_counter (int):
            The index of the assignment to be updated.
        data (str):
            A JSON blob containing data to add to the assignment.
        end_datetime (datetime.datetime):
            The datetime when the previous task assignment was submitted.

    Returns:
        None
    """
    assignment = (TaskAssignment.objects
                  .get(task=task,
                       assignment_counter=assignment_counter))
    assignment.in_progress_task_data = data
    assignment.status = TaskAssignment.Status.PROCESSING
    assignment.save()

    Iteration.objects.create(
        assignment=assignment,
        start_datetime=submit_datetime)


def _call_abort_completion_function(project):
    abort_completion_fn = project.workflow_version.abort_completion_function
    abort_completion_fn_path = abort_completion_fn.get('path', '')
    abort_completion_fn_kwargs = abort_completion_fn.get('kwargs', {})
    if abort_completion_fn_path:
        abort_completion_function = locate(abort_completion_fn_path)
        abort_completion_function(
            project,
            **abort_completion_fn_kwargs)


def end_project(project_id):
    """
    Mark the specified project and its component tasks as aborted.

    Args:
        project_id (int): The ID of the project to abort.

    Returns:
        None
    """
    project = Project.objects.get(id=project_id)
    project.status = Project.Status.ABORTED
    project.save()
    _call_abort_completion_function(project)
    for task in project.tasks.all():
        task.status = Task.Status.ABORTED
        task.save()
        notify_status_change(task, assignment_history(task))
        notify_project_status_change(project)
    archive_project_slack_group(project)


def set_project_status(project_id, status):
    """
    Set the project to the given status. Raise an exception if the status
    is not a valid project status.

    Args:
        project_id (int): The ID of the project
        status (str): The new project status

    Returns:
        None

    Raises:
        orchestra.core.errors.ProjectStatusError:
            The specified new status is not supported.
    """
    project = Project.objects.get(id=project_id)
    status_choices = dict(Project.STATUS_CHOICES)
    if status == status_choices[Project.Status.PAUSED]:
        project.status = Project.Status.PAUSED
        notify_project_status_change(project)
    elif status == status_choices[Project.Status.ACTIVE]:
        project.status = Project.Status.ACTIVE
        notify_project_status_change(project)
    elif status == status_choices[Project.Status.COMPLETED]:
        project.status = Project.Status.COMPLETED
        notify_project_status_change(project)
    elif status == status_choices[Project.Status.ABORTED]:
        raise ProjectStatusError((
            'Try aborting the project with set_project_status. '
            'Use end_project instead.'))
    else:
        raise ProjectStatusError('Invalid project status.')
    project.save()


def _check_creation_policy(step, project):
    """
    Check the creation policy of the given step, which will determine whether
    to create the task.

    Args:
        step (orchestra.models.Step)
        project (orchestra.models.Project)
    Returns:
        success (boolean) if the task should be created.
    Raises:
        orchestra.core.errors.CreationPolicyError:
            The specified creation policy type is not supported or the policy
            failed during execution.
    """
    policy = step.creation_policy.get('policy_function', {})
    policy_path = policy.get('path', '')
    policy_kwargs = policy.get('kwargs', {})
    try:
        policy_function = locate(policy_path)
        prerequisite_data = get_previously_completed_task_data(step, project)
        project_data = project.project_data
        return policy_function(
            prerequisite_data, project_data, **policy_kwargs)
    except Exception as e:
        raise CreationPolicyError(e)


def _preassign_workers(task, policy_type):
    """
    Assign a new task to a worker according to its assignment policy,
    leaving the task unchanged if policy not present.

    Args:
        task (orchestra.models.Task):
            The newly created task to assign.
        policy_type (string):
            The type of assignment policy to use, from the AssignmentPolicyType

    Returns:
        task (orchestra.models.Task):
            The modified task object.

    Raises:
        orchestra.core.errors.AssignmentPolicyError:
            The specified assignment policy type is not supported or a
            machine step is given an assignment policy.
    """
    step = task.step
    policy = step.assignment_policy.get(
        'policy_function', {}).get(policy_type, {})
    policy_path = policy.get('path', '')
    policy_kwargs = policy.get('kwargs', {})

    if not step.is_human:
        if policy:
            raise AssignmentPolicyError('Machine step should not have '
                                        'assignment policy.')
    elif not policy:
        raise AssignmentPolicyError('Assignment policy incorrectly specified.')
    else:
        try:
            policy_function = locate(policy_path)
            task = policy_function(task, **policy_kwargs)
        except Exception as e:
            raise AssignmentPolicyError(e)
    return task


def schedule_machine_tasks(project, steps):
    machine_step_scheduler_class = locate(
        settings.MACHINE_STEP_SCHEDULER['path']
    )
    kwargs = settings.MACHINE_STEP_SCHEDULER.get('kwargs', {})
    machine_step_scheduler = machine_step_scheduler_class(**kwargs)
    for step in steps:
        machine_step_scheduler.schedule(project.id, step.slug)


# TODO(kkamalov): make a periodic job that runs this function periodically
@transaction.atomic
def create_subsequent_tasks(project):
    """
    Create tasks for a given project whose dependencies have been
    completed.

    Args:
        project (orchestra.models.Project):
            The project for which to create tasks.

    Returns:
        project (orchestra.models.Project):
            The modified project object.
    """
    workflow_version = project.workflow_version
    all_steps = workflow_version.steps.all().order_by('id')

    # get all completed tasks associated with a given project
    completed_tasks = Task.objects.filter(status=Task.Status.COMPLETE,
                                          project=project)
    completed_step_slugs = set(completed_tasks.values_list('step__slug',
                                                           flat=True))

    end_project = False
    machine_tasks_to_schedule = []
    for step in all_steps:
        end_project = end_project or (
            step.slug in completed_step_slugs and step.completion_ends_project)

        if step.slug in completed_step_slugs or Task.objects.filter(
                project=project, step=step).exists():
            continue

        if _are_desired_steps_completed_on_project(
                step.creation_depends_on, completed_tasks=completed_tasks):
            if _check_creation_policy(step, project):
                # create new task and task_assignment
                task = Task(step=step,
                            project=project,
                            status=Task.Status.AWAITING_PROCESSING)
                task.save()

                # Apply todolist templates to Task
                for template in task.step.todolist_templates_to_apply.all():
                    add_todolist_template(template.slug, project.id, step.slug)

                _preassign_workers(task, AssignmentPolicyType.ENTRY_LEVEL)

                if not step.is_human:
                    machine_tasks_to_schedule.append(step)

    if len(machine_tasks_to_schedule) > 0:
        connection.on_commit(lambda: schedule_machine_tasks(
            project, machine_tasks_to_schedule))

    incomplete_tasks = (Task.objects.filter(project=project)
                        .exclude(Q(status=Task.Status.COMPLETE) |
                                 Q(status=Task.Status.ABORTED)))

    if end_project or incomplete_tasks.count() == 0:
        if project.status != Project.Status.COMPLETED:
            set_project_status(project.id, 'Completed')
            archive_project_slack_group(project)
