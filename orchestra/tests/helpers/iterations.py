from orchestra.models import Iteration
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.utils.task_properties import current_assignment
from orchestra.utils.task_properties import get_iteration_history


def verify_iterations(task_id):
    task = Task.objects.get(id=task_id)
    iterations = list(get_iteration_history(task).all())
    if iterations:
        _verify_iteration_topology(iterations)
        _verify_iteration_data(iterations)
        _verify_iteration_datetimes(iterations)


def _verify_iteration_topology(iterations):
    # First iteration should belong to first assignment
    expected_counter = 0
    visited_counters = set()
    task = iterations[0].assignment.task
    for i, iteration in enumerate(iterations):
        assignment = iteration.assignment
        assignment_counter = assignment.assignment_counter
        assert assignment_counter == expected_counter
        visited_counters.add(assignment.assignment_counter)

        if i == len(iterations) - 1:
            _verify_final_iteration(iteration)
        else:
            # Only the last iteration (if any) should be processing
            assert iteration.status != Iteration.Status.PROCESSING

        # Status of current iteration determines the expected review level
        # of the next one's assignment
        if iteration.status == Iteration.Status.REQUESTED_REVIEW:
            expected_counter = assignment_counter + 1
        elif iteration.status == Iteration.Status.PROVIDED_REVIEW:
            expected_counter = assignment_counter - 1

    # Iterations should span all assignments
    assert visited_counters == set(range(task.assignments.count()))


def _verify_final_iteration(iteration):
    # Last iteration should belong to current assignment
    assignment = iteration.assignment
    assert assignment == current_assignment(assignment.task)

    # Map final iteration statuses onto task statuses
    task_statuses = {
        Iteration.Status.PROCESSING: [
            Task.Status.PROCESSING, Task.Status.REVIEWING,
            Task.Status.POST_REVIEW_PROCESSING
        ],
        Iteration.Status.REQUESTED_REVIEW: [
            Task.Status.PENDING_REVIEW, Task.Status.COMPLETE
        ],
        Iteration.Status.PROVIDED_REVIEW: [
            Task.Status.POST_REVIEW_PROCESSING
        ]
    }

    # A task awaiting processing should not have iterations
    assignment.task.status != Task.Status.AWAITING_PROCESSING

    for k, v in task_statuses.items():
        # An aborted task could have any iteration configuration
        task_statuses[k].append(Task.Status.ABORTED)

    if iteration.status == Iteration.Status.PROCESSING:
        expected_assignment_status = TaskAssignment.Status.PROCESSING
    else:
        expected_assignment_status = TaskAssignment.Status.SUBMITTED

    # Check that task and assignment statuses are correctly set
    assert assignment.status == expected_assignment_status
    assert assignment.task.status in task_statuses[iteration.status]


def _verify_iteration_data(iterations):
    """
    Verifies correct data for certain iterations.

    Since the data for other iterations won't be stored elsewhere, this
    function should be run each time an iteration is added.
    """
    for iteration in iterations:
        if iteration.status == Iteration.Status.PROCESSING:
            # Iterations should not have data until submitted
            assert iteration.submitted_data == {}
        # NOTE(jrbotros): Last iteration for an assignment will normally
        # have its latest data, unless the task has been reverted


def _verify_iteration_datetimes(iterations):
    """
    Verifies correct start and end datetimes for ordered iterations.
    """
    for iteration in iterations:
        assignment = iteration.assignment
        siblings = assignment.iterations.order_by('start_datetime')
        if siblings.first() == iteration:
            # If iteration is first in assignment, expected start datetime
            # is when the assignment was picked up rather than the end of
            # the previous iteration
            expected_start_datetime = assignment.start_datetime

        assert iteration.start_datetime == expected_start_datetime
        # The expected start datetime for the next iteration should be the
        # end datetime of the current one, unless the next iteration is the
        # first in its assignment
        expected_start_datetime = iteration.end_datetime

        # If iteration is processing, it should not have an end datetime
        if iteration.status == Iteration.Status.PROCESSING:
            assert not iteration.end_datetime
