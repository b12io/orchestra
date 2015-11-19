from importlib import import_module

from orchestra.core.errors import MachineExecutionError
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Step
from orchestra.utils.task_lifecycle import previously_completed_task_data
from orchestra.utils.task_lifecycle import create_subsequent_tasks


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
    count = task.assignments.count()
    if count > 1:
        raise MachineExecutionError('At most 1 assignment per machine task')
    elif count == 1:
        task_assignment = task.assignments.first()
        if task_assignment.status == TaskAssignment.Status.SUBMITTED:
            raise MachineExecutionError('Task assignment completed '
                                        'but task is not!')
    else:
        task_assignment = (
            TaskAssignment.objects
            .create(task=task,
                    status=TaskAssignment.Status.PROCESSING,
                    in_progress_task_data={},
                    snapshots={}))

    prerequisites = previously_completed_task_data(task)

    function_module = import_module(step.execution_function['module'])
    function = getattr(function_module, step.execution_function['name'])
    task_data = function(project.project_data, prerequisites)
    task_assignment.status = TaskAssignment.Status.SUBMITTED
    task_assignment.in_progress_task_data = task_data
    task_assignment.save()
    task.status = Task.Status.COMPLETE
    task.save()

    create_subsequent_tasks(project)
