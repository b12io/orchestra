import logging
from pydoc import locate

from django.db import transaction
from django.utils import timezone

from orchestra.core.errors import MachineExecutionError
from orchestra.models import Iteration
from orchestra.models import Project
from orchestra.models import Step
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import get_previously_completed_task_data
from orchestra.utils.task_properties import get_latest_iteration

logger = logging.getLogger(__name__)


def execute(project_id, step_slug):
    project = Project.objects.get(id=project_id)
    step = Step.objects.get(slug=step_slug,
                            workflow_version=project.workflow_version)
    task = Task.objects.get(project=project,
                            step=step)

    # Run machine function
    if step.is_human:
        raise MachineExecutionError('Step worker type is not machine')

    if task.status == Task.Status.COMPLETE:
        raise MachineExecutionError('Task assignment already completed')

    # Machine tasks are only assigned to one worker/machine,
    # so they should only have one task assignment,
    # and should never be submitted for review.

    with transaction.atomic():
        # Uniqueness constraint on assignnment_counter and task prevents
        # concurrent creation of more than one assignment
        task_assignment, created = TaskAssignment.objects.get_or_create(
            assignment_counter=0,
            task=task,
            defaults={
                'status': TaskAssignment.Status.PROCESSING,
                'in_progress_task_data': {}})
        if created:
            task.status = Task.Status.PROCESSING
            task.save()

            Iteration.objects.create(
                assignment=task_assignment,
                start_datetime=task_assignment.start_datetime)
        else:
            # Task assignment already exists
            if task_assignment.status == TaskAssignment.Status.FAILED:
                # Pick up failed task for reprocessing
                task_assignment.status = TaskAssignment.Status.PROCESSING
                task_assignment.save()
            else:
                # Task assignment already processing
                raise MachineExecutionError(
                    'Task already picked up by another machine')

    prerequisites = get_previously_completed_task_data(task.step, task.project)

    function = locate(step.execution_function['path'])
    kwargs = step.execution_function.get('kwargs', {})
    try:
        project_data = project.project_data
        project_data['project_id'] = project_id
        task_data = function(project_data, prerequisites, **kwargs)
    except Exception:
        task_assignment.status = TaskAssignment.Status.FAILED
        logger.exception('Machine task has failed')
        task_assignment.save()
        return
    task_assignment.status = TaskAssignment.Status.SUBMITTED
    task_assignment.in_progress_task_data = task_data
    task_assignment.save()

    if task.project.status == Project.Status.ABORTED:
        # If a long-running task's project was aborted while running, we ensure
        # the aborted state on the task.
        task.status = Task.Status.ABORTED
        task.save()
    else:
        task.status = Task.Status.COMPLETE
        task.save()

        iteration = get_latest_iteration(task_assignment)
        iteration.status = Iteration.Status.REQUESTED_REVIEW
        iteration.submitted_data = task_data
        iteration.end_datetime = timezone.now()
        iteration.save()

        create_subsequent_tasks(project)
