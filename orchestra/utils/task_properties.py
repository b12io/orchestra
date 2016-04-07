from orchestra.core.errors import TaskAssignmentError
from orchestra.models import Iteration
from orchestra.models import Task
from orchestra.models import TaskAssignment


def assignment_history(task):
    """
    Return all assignments for `task` ordered by `assignment_counter`.

    Args:
        task (orchestra.models.Task):
            The specified task object.

    Returns:
        assignment_history ([orchestra.models.TaskAssignment]):
            All assignments for `task` ordered by `assignment_counter`.
    """
    return task.assignments.order_by('assignment_counter')


def current_assignment(task):
    """
    Return the in-progress assignment for `task`.

    Args:
        task (orchestra.models.Task):
            The specified task object.

    Returns:
        current_assignment (orchestra.models.TaskAssignment):
            The in-progress assignment for `task`.
    """
    assignments = assignment_history(task)
    processing = task.assignments.filter(
        status=TaskAssignment.Status.PROCESSING)
    if not processing.exists():
        return assignments.last()
    else:
        if processing.count() > 1:
            raise TaskAssignmentError(
                'More than one processing assignment for task {}'.format(
                    task.id))
        else:
            return processing.first()


def get_latest_iteration(assignment):
    return assignment.iterations.order_by('start_datetime').last()


def get_iteration_history(task, reverse=False):
    order_expression = 'start_datetime'
    if reverse:
        order_expression = '-' + order_expression
    return (
        Iteration.objects.filter(assignment__task=task)
        .order_by(order_expression))


def last_snapshotted_assignment(task_id):
    task = Task.objects.get(id=task_id)

    assignments = assignment_history(task)
    if not assignments:
        return None

    snapshots = assignments.first().snapshots['snapshots']
    if not snapshots:
        return None

    snapshot = snapshots[0]
    current_assignment_counter = 0
    latest_snapshot_index = [0 for assignment in assignments]
    while True:
        if snapshot['type'] in (TaskAssignment.SnapshotType.SUBMIT,
                                TaskAssignment.SnapshotType.ACCEPT):
            next_assignment_counter = current_assignment_counter + 1
        elif snapshot['type'] == TaskAssignment.SnapshotType.REJECT:
            next_assignment_counter = current_assignment_counter - 1
        else:
            raise Exception('Snapshot status not found.')

        if next_assignment_counter == assignments.count():
            return assignments[current_assignment_counter]

        latest_snapshot_index[current_assignment_counter] += 1

        next_assignment_snapshots = (assignments[next_assignment_counter]
                                     .snapshots['snapshots'])
        try:
            snapshot = (next_assignment_snapshots[
                latest_snapshot_index[next_assignment_counter]])
        except IndexError:
            return assignments[current_assignment_counter]

        current_assignment_counter = next_assignment_counter


def all_workers(task):
    """
    Return all workers for a given task.

    Args:
        task (orchestra.models.Task):
            The specified task object.

    Returns:
        all_workers ([orchestra.models.Worker]):
            A list of all workers involved with `task`.
    """
    return [assignment.worker for assignment in assignment_history(task).all()]


def is_worker_assigned_to_task(worker, task):
    """
    Check if specified worker is assigned to the given task.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.
        task (orchestra.models.Task):
            The given task object.

    Returns:
        worker_assigned_to_task (bool):
            True if worker has existing assignment for the given task.
    """
    return (task.assignments
            .filter(worker=worker)
            .exists())
