from orchestra.core.errors import MachineExecutionError
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.workflow import Step
from orchestra.workflow import get_workflow_by_slug
from orchestra.utils.task_lifecycle import previously_completed_task_data
from orchestra.utils.task_lifecycle import create_subsequent_tasks


def execute(project_id, step_slug):
    project = Project.objects.get(id=project_id)
    workflow = get_workflow_by_slug(project.workflow_slug)
    step = workflow.get_step(step_slug)
    task = Task.objects.get(project=project,
                            step_slug=step_slug)

    # Run machine function
    if step.worker_type != Step.WorkerType.MACHINE:
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

    task_data = step.function(project.project_data, prerequisites)
    task_assignment.status = TaskAssignment.Status.SUBMITTED
    task_assignment.in_progress_task_data = task_data
    task_assignment.save()
    task.status = Task.Status.COMPLETE
    task.save()

    create_subsequent_tasks(project)
