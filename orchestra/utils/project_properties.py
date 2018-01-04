from django.db.models import Count
from django.db.models import Q

from orchestra.models import Project
from orchestra.models import Task


def _in_progress_project_ids():
    return (Task.objects.exclude(Q(status=Task.Status.COMPLETE) |
                                 Q(status=Task.Status.ABORTED))
            .values_list('project', flat=True))


def completed_projects(projects):
    """
    Filters `projects` queryset to completed ones.

    TODO(marcua): if we use this for business logic, we should also ensure
    that the number of tasks equals the number of steps in the workflow, which
    will be easier after @thisisdhaas implements workflows-near-the-db.  It
    would be cleaner to just add a Complete state to Projects at that point.
    """
    projects = projects.filter(status=Project.Status.ACTIVE)
    return (
        projects.annotate(num_tasks=Count('tasks'))
        .filter(num_tasks__gt=0)
        .exclude(id__in=_in_progress_project_ids()))


def incomplete_projects(projects):
    return projects.filter(id__in=_in_progress_project_ids())
