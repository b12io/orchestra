from orchestra.models import Task


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
    if task.status == Task.Status.POST_REVIEW_PROCESSING:
        # Get second-to-last assignment, since reviewer rejected
        return assignments.reverse()[1]
    else:
        return assignments.last()


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
