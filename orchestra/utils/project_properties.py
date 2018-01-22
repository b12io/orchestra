from django.db.models import Count
from django.db.models import Q

from orchestra.models import Project
from orchestra.models import Task


def completed_projects(projects):
    """
    Filters `projects` queryset to completed ones.

    TODO(marcua): if we use this for business logic, we should also ensure
    that the number of tasks equals the number of steps in the workflow, which
    will be easier after @thisisdhaas implements workflows-near-the-db.  It
    would be cleaner to just add a Complete state to Projects at that point.
    """
    projects = projects.filter(status=Project.Status.ACTIVE)
    in_progress_projects = (
        Task.objects.exclude(status=Task.Status.COMPLETE)
        .values_list('project', flat=True))
    return (
        projects.annotate(num_tasks=Count('tasks'))
        .filter(num_tasks__gt=0)
        .exclude(id__in=in_progress_projects))


def incomplete_projects(projects):
    incomplete_project_ids = (
        Task.objects.exclude(Q(status=Task.Status.COMPLETE) |
                             Q(status=Task.Status.ABORTED))
        .values_list('project', flat=True))
    return projects.filter(id__in=incomplete_project_ids)
