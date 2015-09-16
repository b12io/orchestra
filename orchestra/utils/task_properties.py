from orchestra.models import Task


def assignment_history(task):
    return task.assignments.order_by('assignment_counter')


def current_assignment(task):
    assignments = assignment_history(task)
    if task.status == Task.Status.POST_REVIEW_PROCESSING:
        # Get second-to-last assignment, since reviewer rejected
        return assignments.reverse()[1]
    else:
        return assignments.last()


def all_workers(task):
    return [assignment.worker for assignment in assignment_history(task).all()]


def is_worker_assigned_to_task(worker, task):
    return (task.assignments
            .filter(worker=worker)
            .exists())
