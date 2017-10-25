import logging

from orchestra.core.errors import AssignmentPolicyError
from orchestra.core.errors import WorkerCertificationError
from orchestra.models import Task
from orchestra.models import Worker
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_properties import assignment_history

logger = logging.getLogger(__name__)


def anyone_certified(task, **kwargs):
    """
    Default assignment policy, we leave the task
    in the awaiting processing pool.
    """
    return task


def specified_worker(task, username, **kwargs):
    """
    Assign task to a specific person.

    Args:
        username (str):
            Username of the worker to assign.

    Returns:
        task (orchestra.models.Task): The modified task object.
    """
    worker = Worker.objects.get(user__username=username)
    return assign_task(worker.id, task.id)


def previously_completed_steps(task, related_steps, **kwargs):
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
    if related_steps is None:
        raise AssignmentPolicyError('No related steps given')

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
            except WorkerCertificationError:
                # Task could not be assigned to related worker, try with
                # another related worker
                logger.warning('Tried to assign worker %s to step %s, for '
                               'which they are not certified',
                               entry_level_assignment.worker.id,
                               task.step.slug, exc_info=True)
            except Exception:
                logger.warning('Unable to assign task.', exc_info=True)
    return task
