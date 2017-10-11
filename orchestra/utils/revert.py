from enum import Enum

from django.db import transaction

from orchestra.core.errors import InvalidRevertError
from orchestra.models import Iteration
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.project_api.serializers import IterationSerializer
from orchestra.project_api.serializers import TaskAssignmentSerializer
from orchestra.project_api.serializers import TaskSerializer
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import get_iteration_history
from orchestra.utils.task_properties import get_latest_iteration


class RevertChange(Enum):
    UNCHANGED = 0
    REVERTED = 1
    DELETED = 2


@transaction.atomic
def revert_task_to_iteration(task_id, iteration_id,
                             revert_before=False, commit=False):
    """
    Reverts a task to or before a specified iteration.

    Args:
        task (orchestra.models.Task):
            The ID of the task to be reverted.
        iteration_id (datetime.datetime):
            The ID of the iteration before which to revert the task.
        revert_before (bool):
            If `revert_before` is indicated, the task will be reverted to a
            state before the specified iteration was created; otherwise, it
            will be reverted to a state in which the iteration is processing.
            This can only be true for the first iteration in an assignment.
        commit (bool):
            Determines whether the revert is actually carried out;
            otherwise, an audit trail is passively generated.

    Returns:
        audit (dict):
            An audit trail for the revert, e.g.,
            {
                'task': {...},
                'assignments': [
                    {
                        # worker_0 assignment
                        'assignment': {...},
                        'change': 1,
                        'iterations': [
                            {
                                'iteration': {...},
                                'change': 2
                            }
                        ]
                    },
                    {
                        # worker_1 assignment
                        'assignment': {...},
                        'change': 2,
                        'iterations': []
                    }
                ],
            }
    """
    task = Task.objects.get(id=task_id)
    revert_iteration = Iteration.objects.get(id=iteration_id)
    first_iteration = (
        revert_iteration.assignment.iterations
                        .order_by('start_datetime').first())
    if revert_before and revert_iteration != first_iteration:
        raise InvalidRevertError(
            "Cannot revert before an iteration that isn't the first of "
            "its assignment.")

    task_audit = _build_revert_audit(task, revert_iteration, revert_before)
    if commit:
        _revert_task_from_audit(task_audit)
    return task_audit


def _revert_task_from_audit(task_audit):
    task = Task.objects.get(id=task_audit['task']['id'])
    task.status = task_audit['reverted_status']
    task.save()
    for assignment_audit in task_audit['assignments']:
        _revert_assignment_from_audit(assignment_audit)


def _revert_assignment_from_audit(assignment_audit):
    assignment = TaskAssignment.objects.get(
        id=assignment_audit['assignment']['id'])
    if assignment_audit['change'] == RevertChange.DELETED.value:
        assignment.delete()
    elif assignment_audit['change'] == RevertChange.REVERTED.value:
        for iteration_audit in assignment_audit['iterations']:
            _revert_iteration_from_audit(iteration_audit)

        assignment.refresh_from_db()
        if get_latest_iteration(
                assignment).status == Iteration.Status.PROCESSING:
            assignment.status = TaskAssignment.Status.PROCESSING
        else:
            assignment.status = TaskAssignment.Status.SUBMITTED
        assignment.save()

        # TODO(jrbotros): Right now, we're leaving the latest assignment
        # `in_progress_task_data` alone since we would otherwise lose it;
        # when we implement archival rather than deletion, we should update
        # the latest assignment data to the submitted data of the iteration
        # reverted to.

    return assignment


def _revert_iteration_from_audit(iteration_audit):
    iteration = Iteration.objects.get(
        id=iteration_audit['iteration']['id'])
    if iteration_audit['change'] == RevertChange.DELETED.value:
        iteration.delete()
    elif iteration_audit['change'] == RevertChange.REVERTED.value:
        iteration = Iteration.objects.get(
            id=iteration_audit['iteration']['id'])
        iteration.status = Iteration.Status.PROCESSING
        iteration.end_datetime = None
        iteration.submitted_data = {}
        iteration.save()


def _build_revert_audit(task, revert_iteration, revert_before):
    if task.status == Task.Status.ABORTED:
        raise InvalidRevertError('Cannot revert aborted task.')

    task_audit = {
        'task': TaskSerializer(task).data,
        'assignments': [],
    }

    for assignment in assignment_history(task).all():
        assignment_audit = (
            _build_assignment_revert_audit(
                assignment, revert_iteration, revert_before))
        task_audit['assignments'].append(assignment_audit)

    task_audit['reverted_status'] = _reverted_task_status(
        task_audit, revert_before)
    return task_audit


def _build_assignment_revert_audit(assignment, revert_iteration,
                                   revert_before):
    assignment_audit = {
        'assignment': TaskAssignmentSerializer(assignment).data,
        'change': RevertChange.UNCHANGED.value,
        'iterations': []
    }

    for iteration in assignment.iterations.order_by('start_datetime').all():
        iteration_audit = (
            _build_iteration_revert_audit(
                iteration, revert_iteration, revert_before))
        assignment_audit['iterations'].append(iteration_audit)

    changed_iterations = _parse_changed_items(
        assignment_audit['iterations'], 'iteration')
    deleted_iterations = changed_iterations[RevertChange.DELETED.value]
    reverted_iterations = changed_iterations[RevertChange.REVERTED.value]

    if len(deleted_iterations) == assignment.iterations.count():
        assignment_audit['change'] = RevertChange.DELETED.value
    elif deleted_iterations or reverted_iterations:
        assignment_audit['change'] = RevertChange.REVERTED.value
    return assignment_audit


def _build_iteration_revert_audit(iteration, revert_iteration, revert_before):
    iteration_audit = {
        'iteration': IterationSerializer(iteration).data,
        'change': RevertChange.UNCHANGED.value,
    }
    if revert_before:
        if (iteration.id == revert_iteration.id or
                iteration.start_datetime >= revert_iteration.start_datetime):
            iteration_audit['change'] = RevertChange.DELETED.value
    else:
        if iteration.id == revert_iteration.id:
            iteration_audit['change'] = RevertChange.REVERTED.value
        elif iteration.start_datetime > revert_iteration.start_datetime:
            iteration_audit['change'] = RevertChange.DELETED.value
    return iteration_audit


def _reverted_task_status(task_audit, revert_before):
    """
    Reverts the status of an otherwise-reverted task.

    Args:
        task (dict):
            Audit containing task data to be changed upon revert.

    Returns:
        status (orchestra.models.Task.Status):
            The status of the task if it were reverted.
    """
    task = Task.objects.get(id=task_audit['task']['id'])

    flattened_iterations = [
        iteration_audit
        for assignment_audit in task_audit['assignments']
        for iteration_audit in assignment_audit['iterations']]
    changed_items = _parse_changed_items(flattened_iterations, 'iteration')

    latest_iterations = (
        get_iteration_history(task, reverse=True)
        .exclude(id__in=changed_items[RevertChange.DELETED.value]))

    num_iterations = latest_iterations.count()
    if num_iterations == 0:
        return Task.Status.AWAITING_PROCESSING
    elif revert_before:
        # Reverting before the first iteration in an assignment means the task
        # is pending review, since at least one iteration exists
        return Task.Status.PENDING_REVIEW
    else:
        # Revert to a processing iteration state
        if num_iterations == 1:
            return Task.Status.PROCESSING
        else:
            previous_status = latest_iterations[1].status
            if previous_status == Iteration.Status.REQUESTED_REVIEW:
                return Task.Status.REVIEWING
            else:
                return Task.Status.POST_REVIEW_PROCESSING


def _parse_changed_items(items, item_key):
    changed_items = {change.value: [] for change in RevertChange}
    for item in items:
        changed_items[item['change']].append(item[item_key]['id'])
    return changed_items
