from orchestra.models import Project
from orchestra.workflow import get_workflow_by_slug
from orchestra.project_api.serializers import TaskSerializer

import logging

logger = logging.getLogger(__name__)


class MalformedDependencyException(Exception):
    pass


def get_project_task_data(project_id):
    project = Project.objects.get(id=project_id)

    tasks = {}
    for task in project.tasks.all():
        tasks[task.step_slug] = TaskSerializer(task).data

    return tasks


def get_workflow_steps(workflow_slug):
    """Get a sorted list of steps for a project

    Returns a list of (slug, short_description) tuples topologically sorted so
    that earlier steps are prerequisites for later ones. """

    workflow = get_workflow_by_slug(workflow_slug)

    # Build a directed graph of the step dependencies
    graph = {}
    for step in workflow.get_steps():
        graph[step.slug] = [dependency.slug for dependency
                            in step.creation_depends_on]

    queue = []
    for key, value in graph.items():
        if value == []:
            queue.append(key)

    # TODO(derek): prevent the MalformedDependencyExceptions from being
    # possible by baking protection into the Workflow/Step classes
    if not len(queue):
        raise MalformedDependencyException("All %s workflow steps have "
                                           "dependencies. There is no start "
                                           "point." % workflow_slug)

    # Build the steps list in order using a breadth-first-like traversal of the
    # step dependency graph
    steps = []
    already_added = set()
    while len(queue):
        current_node = queue.pop(0)

        if current_node in already_added:
            continue

        already_added.add(current_node)
        steps.append((current_node,
                      workflow.get_step(current_node).description))
        for key, dependencies in graph.items():
            if (current_node in dependencies and
                    key not in already_added):
                queue.append(key)

    return steps
