import random
from importlib import import_module

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from orchestra.core.errors import AssignmentPolicyError
from orchestra.core.errors import IllegalTaskSubmission
from orchestra.core.errors import ModelSaveError
from orchestra.core.errors import NoTaskAvailable
from orchestra.core.errors import ReviewPolicyError
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import TaskDependencyError
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import WorkerCertificationError
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.project_api.serializers import TaskSerializer
from orchestra.project_api.serializers import TaskAssignmentSerializer
from orchestra.slack import add_worker_to_project_team
from orchestra.utils.assignment_snapshots import empty_snapshots
from orchestra.utils.notifications import notify_status_change
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import current_assignment
from orchestra.utils.task_properties import last_snapshotted_assignment
from orchestra.utils.task_properties import is_worker_assigned_to_task

import logging
logger = logging.getLogger(__name__)


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
    # # TODO(jrbotros): allow per-user exception to task limit
    # return (TaskAssignment.objects
    #         .filter(worker=worker,
    #                 status=TaskAssignment.Status.PROCESSING,
    #                 task__status=Task.Status.PROCESSING)
    #         .count()) >= settings.ORCHESTRA_MAX_IN_PROGRESS_TASKS
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


def _worker_certified_for_task(worker, task, role,
                               task_class=WorkerCertification.TaskClass.REAL):
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

    Returns:
        certified_for_task (bool):
            True if worker is certified for a given task, role, and task
            class.
    """
    step = task.step
    match_count = (
        WorkerCertification
        .objects
        .filter(worker=worker,
                role=role,
                task_class=task_class,
                certification__in=step.required_certifications.all())
        .count())
    certified_for_task = step.required_certifications.count() == match_count
    return certified_for_task


@transaction.atomic
def assign_task(worker_id, task_id):
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

    roles = {
        Task.Status.AWAITING_PROCESSING: WorkerCertification.Role.ENTRY_LEVEL,
        Task.Status.PENDING_REVIEW: WorkerCertification.Role.REVIEWER
    }

    required_role = roles.get(task.status)
    if required_role is None:
        raise TaskAssignmentError('Status incompatible with new assignment')

    assignment = current_assignment(task)
    if not _worker_certified_for_task(worker, task, required_role):
        raise WorkerCertificationError('Worker not certified for this task.')
    if is_worker_assigned_to_task(worker, task):
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

    (TaskAssignment.objects
        .create(worker=worker,
                task=task,
                status=TaskAssignment.Status.PROCESSING,
                assignment_counter=assignment_counter,
                in_progress_task_data=in_progress_task_data,
                snapshots=empty_snapshots()))

    add_worker_to_project_team(worker, task.project)
    notify_status_change(task, previous_status)
    return task


@transaction.atomic
def reassign_assignment(worker_id, assignment_id):
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

    if not _worker_certified_for_task(worker, assignment.task, role):
        raise WorkerCertificationError(
            'Worker not certified for this assignment.')
    if is_worker_assigned_to_task(worker, assignment.task):
        raise TaskAssignmentError('Worker already assigned to this task.')

    assignment.worker = worker
    assignment.save()
    add_worker_to_project_team(worker, assignment.task.project)

    return assignment


@transaction.atomic
def complete_and_skip_task(task_id):
    """
    Marks a task and its assignments as complete and creates subsequent tasks.

    Args:
        task_id (int):
            The ID of the task to be marked as complete and skipped.

    Returns:
        task (orchestra.models.Task):
            The completed and skipped task.
    """
    task = Task.objects.get(id=task_id)
    task.status = Task.Status.COMPLETE
    task.save()
    for assignment in task.assignments.all():
        assignment.status = TaskAssignment.Status.SUBMITTED
        assignment.save()
    create_subsequent_tasks(task.project)
    return task


@transaction.atomic
def revert_task_to_datetime(task_id, revert_datetime, fake=False):
    """
    Reverts a task to its state immediately before the specified
    datetime.

    Args:
        task_id (int):
            The ID of the task to be reverted.
        revert_datetime (datetime.datetime):
            The datetime before which to revert the task.
        fake (bool):
            Determines whether the revert is actually carried out;
            otherwise, an audit trail is passively generated.

    Returns:
        audit (dict):
            An audit trail for the revert, e.g.,

            {
                'task': {...},
                'change': 'reverted'
                'assignments': [
                    {
                        # worker_0 assignment
                        'assignment': {...},
                        'change': 'reverted',
                        'snapshots': [
                            {
                                'snapshot': {...},
                                'change': 'unchanged'
                            }
                            {
                                'snapshot': {...},
                                'change': 'deleted'
                            },
                        ]
                    },
                    {
                        # worker_1 assignment
                        'assignment': {...},
                        'change': 'deleted',
                        'snapshots': [
                            {
                                'snapshot': {...},
                                'change': 'deleted'
                            },
                            {
                                'snapshot': {...},
                                'change': 'deleted'
                            }
                        ]
                    }
                ],
            }
    """
    task = Task.objects.get(id=task_id)
    audit = {
        'task': TaskSerializer(task).data,
        'change': 'unchanged',
        'assignments': []
    }
    reverted = False

    for assignment in assignment_history(task).all():
        assignment_audit = _revert_assignment_to_datetime(
            assignment, revert_datetime, fake)
        audit['assignments'].append(assignment_audit)
        if assignment_audit['change'] != 'unchanged':
            reverted = True

    # Delete task if it starts after revert_datetime
    if task.start_datetime >= revert_datetime:
        audit['change'] = 'deleted'
        if not fake:
            task.delete()
    elif reverted:
        audit['change'] = 'reverted'
        if not fake:
            _revert_task_status(task)

    return audit


def _revert_assignment_to_datetime(assignment, revert_datetime, fake=False):
    """
    Reverts an assignment to its state immediately before the specified
    datetime.

    Args:
        assignment (orchestra.models.TaskAssignment):
            The assignment to be reverted.
        revert_datetime (datetime.datetime):
            The datetime before which to revert the assignment.
        fake (bool):
            Determines whether the revert is actually carried out;
            otherwise, an audit trail is passively generated.

    Returns:
        audit (dict):
            An audit trail for the revert, e.g.,

            {
                'assignment': {...},
                'change': 'reverted',
                'snapshots': [
                    {
                        'snapshot': {...},
                        'change': 'deleted'
                    },
                    {
                        'snapshot': {},
                        'change': 'unchanged'
                    }
                ]
            }
    """
    audit = {
        'assignment': TaskAssignmentSerializer(assignment).data,
        'change': 'unchanged',
        'snapshots': [{'snapshot': snapshot, 'change': 'unchanged'}
                      for snapshot in assignment.snapshots['snapshots']],
    }
    # Revert assignment to datetime by removing snapshots
    gt_idx = None
    snapshots = assignment.snapshots['snapshots']
    for i, snapshot in enumerate(snapshots):
        if parse_datetime(snapshot['datetime']) >= revert_datetime:
            gt_idx = i
            break
    if gt_idx is not None:
        # Revert to before this snapshot
        audit['change'] = 'reverted'
        for i, _ in enumerate(audit['snapshots']):
            if i >= gt_idx:
                audit['snapshots'][i]['change'] = 'deleted'
        if not fake:
            assignment.snapshots['snapshots'] = snapshots[:gt_idx]
            # Reset assignment data to the oldest deleted snapshot. When
            # we determine which assignment is processing in
            # _revert_task_status, we'll revert all other assignments
            # to their latest submitted snapshot data.
            assignment.in_progress_task_data = snapshots[gt_idx]['data']
            assignment.save()

    if assignment.start_datetime >= revert_datetime:
        audit['change'] = 'deleted'
        if not fake:
            # Delete assignments created after the revert datetime.
            assignment.delete()

    return audit


def _revert_task_status(task):
    """
    Reverts the status of an otherwise-reverted task.

    Args:
        task (orchestra.models.Task):
            The task with status to revert.

    Returns:
        task (orchestra.models.Task):
            The task with reverted status.
    """
    assignments = assignment_history(task)
    num_assignments = assignments.count()

    reverted_status = None
    current_assignment_counter = None
    previous_assignment_counter = None
    if num_assignments == 0:
        # No assignment is present
        reverted_status = Task.Status.AWAITING_PROCESSING
    else:
        assignment = last_snapshotted_assignment(task.id)
        if not assignment:
            # Task has an assignment but no snapshots
            reverted_status = Task.Status.PROCESSING
            current_assignment_counter = 0
        else:
            latest_counter = assignment.assignment_counter
            snapshot = assignment.snapshots['snapshots'][-1]
            if snapshot['type'] == TaskAssignment.SnapshotType.REJECT:
                # Task was last rejected back to previous worker
                reverted_status = Task.Status.POST_REVIEW_PROCESSING
                current_assignment_counter = latest_counter - 1
                previous_assignment_counter = latest_counter

            elif (snapshot['type'] in (TaskAssignment.SnapshotType.SUBMIT,
                                       TaskAssignment.SnapshotType.ACCEPT)):
                if latest_counter == num_assignments - 1:
                    # Task was last submitted and no higher-level
                    # assignments are present (reverted tasks will never end
                    # in a completed state)
                    reverted_status = Task.Status.PENDING_REVIEW
                else:
                    reverted_status = Task.Status.REVIEWING
                    previous_assignment_counter = latest_counter
                    current_assignment_counter = latest_counter + 1

    if current_assignment_counter is not None:
        current_assignment = task.assignments.get(
            assignment_counter=current_assignment_counter)
        current_assignment.status = TaskAssignment.Status.PROCESSING
        current_assignment.save()

    if previous_assignment_counter is not None:
        previous_assignment = task.assignments.get(
            assignment_counter=previous_assignment_counter)
        previous_assignment.status = TaskAssignment.Status.SUBMITTED
        previous_assignment.save()

    # TODO(jrbotros): The revert methos should "peel off" snapshots,
    # rather than deleting them in bulk and recalculating the assignment
    # and task statuses; this logic needs to be cleaned up.
    for assignment in task.assignments.all():
        if assignment.status == TaskAssignment.Status.SUBMITTED:
            latest_snapshot = assignment.snapshots['snapshots'][-1]
            assignment.in_progress_task_data = latest_snapshot['data']
            assignment.save()

    task.status = reverted_status
    task.save()
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
    workflow_version = step.workflow_version
    workflow = workflow_version.workflow
    prerequisites = previously_completed_task_data(task)

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
            'id': task.project.id,
            'details': task.project.short_description,
            'team_messages_url': task.project.team_messages_url,
            'project_data': task.project.project_data
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
        'work_times_seconds': [
            snapshot['work_time_seconds']
            for snapshot in task_assignment.snapshots['snapshots']]
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
    if not is_worker_assigned_to_task(worker, task):
        raise TaskAssignmentError('Worker is not associated with task')
    task_details = get_task_details(task_id)

    task_assignment = TaskAssignment.objects.get(worker=worker,
                                                 task=task)
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
        .order_by('-task__project__priority',
                  'task__project__start_datetime'))

    inactive_task_assignments = (
        valid_task_assignments
        .filter(
            worker=worker,
            status=TaskAssignment.Status.SUBMITTED
        )
        .exclude(task__status=Task.Status.COMPLETE)
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
    # recent 20 tasks.
    complete_task_assignments = (
        valid_task_assignments
        .filter(worker=worker,
                task__status=Task.Status.COMPLETE)
        .order_by('-task__project__priority',
                  '-task__project__start_datetime')[:20])

    task_assignments_overview = {
        'returned': (
            active_task_assignments
            .filter(task__status=Task.Status.POST_REVIEW_PROCESSING)),
        'in_progress': (
            active_task_assignments
            .exclude(task__status=Task.Status.POST_REVIEW_PROCESSING)),
        'pending_review': inactive_review_task_assignments,
        'pending_processing': inactive_processing_task_assignments,
        'complete': complete_task_assignments}

    tasks_assigned = {}
    for state, task_assignments in iter(task_assignments_overview.items()):
        tasks_val = []
        for task_assignment in task_assignments:
            step = task_assignment.task.step
            workflow_version = step.workflow_version

            # TODO(marcua): project should be workflow here, no?
            tasks_val.append({'id': task_assignment.task.id,
                              'step': step.name,
                              'project': workflow_version.name,
                              'detail':
                              task_assignment.task.project.short_description})
        tasks_assigned[state] = tasks_val
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
    policy = policy_dict.get('policy', None)
    sample_rate = policy_dict.get('rate', None)
    max_reviews = policy_dict.get('max_reviews', None)

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


def get_next_task_status(task, snapshot_type):
    """
    Given current task status and snapshot type provide new task status.
    If the second level reviewer rejects a task then initial reviewer
    cannot reject it further down, but must fix and submit the task.

    Args:
        task (orchestra.models.Task):
            The specified task object.
        task_status (orchestra.models.TaskAssignment.SnapshotType):
            The action to take upon task submission (e.g., SUBMIT,
            ACCEPT, REJECT).

    Returns:
        next_status (orchestra.models.Task.Status):
            The next status of `task`, once the `snapshot_type` action
            has been completed.

    Raises:
        orchestra.core.errors.IllegalTaskSubmission:
            The `snapshot_type` action cannot be taken for the task in
            its current status.
    """
    if snapshot_type == TaskAssignment.SnapshotType.SUBMIT:
        if task.status == Task.Status.PROCESSING:
            if _is_review_needed(task):
                return Task.Status.PENDING_REVIEW
            return Task.Status.COMPLETE
        elif task.status == Task.Status.POST_REVIEW_PROCESSING:
            return Task.Status.REVIEWING
        raise IllegalTaskSubmission('Worker can only submit a task.')
    elif snapshot_type == TaskAssignment.SnapshotType.REJECT:
        if task.status == Task.Status.REVIEWING:
            return Task.Status.POST_REVIEW_PROCESSING
        raise IllegalTaskSubmission('Only reviewer can reject the task.')
    elif snapshot_type == TaskAssignment.SnapshotType.ACCEPT:
        if task.status == Task.Status.REVIEWING:
            if _is_review_needed(task):
                return Task.Status.PENDING_REVIEW
            return Task.Status.COMPLETE
        raise IllegalTaskSubmission('Only reviewer can accept the task.')
    raise IllegalTaskSubmission('Unknown task state.')


def _check_worker_allowed_new_assignment(worker, task_status):
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
    valid_statuses = [Task.Status.AWAITING_PROCESSING,
                      Task.Status.PENDING_REVIEW]
    if task_status not in valid_statuses:
        raise TaskStatusError('Invalid status for new task assignment.')
    elif worker_assigned_to_rejected_task(worker):
        raise TaskAssignmentError('Worker has pending reviewer feedback that '
                                  'must be addressed.')
    elif worker_assigned_to_max_tasks(worker):
        raise TaskAssignmentError('Worker assigned to max number of tasks.')


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
    _check_worker_allowed_new_assignment(worker, task_status)

    tasks = (Task.objects
             .filter(status=task_status)
             .exclude(assignments__worker=worker)
             .order_by('-project__priority')
             .order_by('project__start_datetime'))

    certification_error = False
    for task in tasks.iterator():
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
    if not is_worker_assigned_to_task(worker, task):
        raise TaskAssignmentError('Worker is not associated with task')

    # Use select_for_update to prevent concurrency issues with submit_task.
    # See https://github.com/unlimitedlabs/orchestra/issues/2.
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
def submit_task(task_id, task_data, snapshot_type, worker, work_time_seconds):
    """
    Returns a dict mapping task prerequisites onto their
    latest task assignment information.  The dict is of the form:
    {'previous-slug': {task_assignment_data}, ...}

    Args:
        task_id (int):
            The ID of the task to submit.
        task_data (str):
            A JSON blob of task data to submit.
        snapshot_type (orchestra.models.TaskAssignment.SnapshotType):
            The action to take upon task submission (e.g., SUBMIT,
            ACCEPT, REJECT).
        worker (orchestra.models.Worker):
            The worker submitting the task.
        work_time_seconds (int):
            The time taken by the worker on the latest iteration of
            their task assignment.

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
    task = Task.objects.select_related('step', 'project').get(id=task_id)
    step = task.step
    if not _are_desired_steps_completed_on_project(step.submission_depends_on,
                                                   project=task.project):
        raise IllegalTaskSubmission('Submission prerequisites are not '
                                    'complete.')

    if task.status == Task.Status.COMPLETE:
        raise TaskStatusError('Task already completed')

    # Use select_for_update to prevent concurrency issues with save_task.
    # See https://github.com/unlimitedlabs/orchestra/issues/2.
    assignments = (TaskAssignment.objects.select_for_update()
                                 .filter(worker=worker, task=task))

    # Worker can belong to only one assignment for a given task.
    if not assignments.count() == 1:
        raise TaskAssignmentError(
            'Task assignment with worker is in broken state.')

    assignment = assignments[0]

    if assignment.status != TaskAssignment.Status.PROCESSING:
        raise IllegalTaskSubmission('Worker is not allowed to submit')

    next_status = get_next_task_status(task, snapshot_type)

    assignment.in_progress_task_data = task_data
    assignment.snapshots['snapshots'].append(
        {'data': assignment.in_progress_task_data,
         'datetime': timezone.now().isoformat(),
         'type': snapshot_type,
         'work_time_seconds': work_time_seconds
         })

    assignment.status = TaskAssignment.Status.SUBMITTED
    assignment.save()
    previous_status = task.status
    task.status = next_status
    task.save()

    if task.status == Task.Status.REVIEWING:
        update_related_assignment_status(task,
                                         assignment.assignment_counter + 1,
                                         assignment.in_progress_task_data)
    elif task.status == Task.Status.POST_REVIEW_PROCESSING:
        update_related_assignment_status(task,
                                         assignment.assignment_counter - 1,
                                         assignment.in_progress_task_data)
    elif task.status == Task.Status.COMPLETE:
        create_subsequent_tasks(task.project)

    notify_status_change(task, previous_status)
    return task


def previously_completed_task_data(task):
    """
    Returns a dict mapping task prerequisites onto their
    latest task assignment information.  The dict is of the form:
    {'previous-slug': {task_assignment_data}, ...}

    Args:
        task (orchestra.models.Task): The specified task object.

    Returns:
        prerequisites (dict):
            A dict mapping task prerequisites onto their latest task
            assignment information.
    """
    step = task.step
    prerequisites = {}

    for required_step in step.creation_depends_on.all():
        required_task = Task.objects.get(step=required_step,
                                         project=task.project)
        if required_task.status != Task.Status.COMPLETE:
            raise TaskDependencyError('Task depenency is not satisfied')

        task_details = get_task_details(required_task.id)

        assignment = assignment_history(required_task).last()
        task_assignment_details = {}
        if assignment:
            # Task assignment should be present unless task was skipped.
            task_assignment_details = get_task_assignment_details(assignment)
        task_assignment_details.update(task_details)

        # TODO(kkamalov): check for circular prerequisites
        prerequisites[required_step.slug] = task_assignment_details
    return prerequisites


def update_related_assignment_status(task, assignment_counter, data):
    """
    Copy data to a specified task assignment and mark it as processing.

    Args:
        task (orchestra.models.Task):
            The task whose assignments will be updated.
        assignment_counter (int):
            The index of the assignment to be updated.
        data (str):
            A JSON blob containing data to add to the assignment.

    Returns:
        None
    """
    assignment = (TaskAssignment.objects
                  .get(task=task,
                       assignment_counter=assignment_counter))
    assignment.in_progress_task_data = data
    assignment.status = TaskAssignment.Status.PROCESSING
    assignment.save()


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
    for task in project.tasks.all():
        task.status = Task.Status.ABORTED
        task.save()
        notify_status_change(task, assignment_history(task))


def _preassign_workers(task):
    """
    Assign a new task to a worker according to its assignment policy,
    leaving the task unchanged if policy not present.

    Args:
        task (orchestra.models.Task):
            The newly created task to assign.

    Returns:
        task (orchestra.models.Task):
            The modified task object.

    Raises:
        orchestra.core.errors.AssignmentPolicyError:
            The specified assignment policy type is not supported or a
            machine step is given an assignment policy.
    """
    step = task.step
    policy = step.assignment_policy.get('policy')
    related_steps = step.assignment_policy.get('steps')

    if not step.is_human:
        if policy:
            raise AssignmentPolicyError('Machine step should not have '
                                        'assignment policy.')
    elif (policy == 'previously_completed_steps'
            and related_steps is not None):
        task = _assign_worker_from_previously_completed_steps(task,
                                                              related_steps)
    elif policy == 'anyone_certified':
        # Leave the task in the awaiting processing pool
        pass
    else:
        raise AssignmentPolicyError('Assignment policy incorrectly specified.')
    return task


def _assign_worker_from_previously_completed_steps(task, related_steps):
    """
    Assign a new task to the entry-level worker of the specified tasks.
    If no worker can be assigned, return the unmodified task.

    Args:
        task (orchestra.models.Task):
            The newly created task to assign.
        related_steps ([str]):
            List of step slugs from which to attempt to assign a worker.

    Returns:
        task (orchestra.models.Task): The modified task object.

    Raises:
        orchestra.core.errors.AssignmentPolicyError:
            Machine steps cannot be included in an assignment policy.
    """
    workflow_version = task.step.workflow_version
    for step_slug in related_steps:
        step = workflow_version.steps.get(slug=step_slug)
        if not step.is_human:
            raise AssignmentPolicyError('Machine step should not be '
                                        'member of assignment policy')
    related_tasks = (
        Task.objects
        .filter(step__slug__in=related_steps, project=task.project)
        .select_related('step'))
    for related_task in related_tasks:
        entry_level_assignment = assignment_history(related_task).first()
        if entry_level_assignment and entry_level_assignment.worker:
            try:
                return assign_task(entry_level_assignment.worker.id, task.id)
            except Exception:
                # Task could not be assigned to related worker, try with
                # another related worker
                logger.warning('Tried to assign worker %s to step %s, for '
                               'which they are not certified',
                               entry_level_assignment.worker.id,
                               task.step.slug, exc_info=True)
    return task


# TODO(kkamalov): make a periodic job that runs this function periodically
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
    all_steps = workflow_version.steps.all()

    # get all completed tasks associated with a given project
    completed_tasks = Task.objects.filter(status=Task.Status.COMPLETE,
                                          project=project)
    completed_step_slugs = set(completed_tasks.values_list('step__slug',
                                                           flat=True))
    for step in all_steps:
        if step.slug in completed_step_slugs or Task.objects.filter(
                project=project, step=step).exists():
            continue

        if _are_desired_steps_completed_on_project(
                step.creation_depends_on, completed_tasks=completed_tasks):
            # create new task and task_assignment
            task = Task(step=step,
                        project=project,
                        status=Task.Status.AWAITING_PROCESSING)
            task.save()

            _preassign_workers(task)
            if not step.is_human:
                machine_step_scheduler_module = import_module(
                    settings.MACHINE_STEP_SCHEDULER[0])
                machine_step_scheduler_class = getattr(
                    machine_step_scheduler_module,
                    settings.MACHINE_STEP_SCHEDULER[1])
                machine_step_scheduler = machine_step_scheduler_class()
                machine_step_scheduler.schedule(project.id, step.slug)
