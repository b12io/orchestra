from django.db.models import Q

from orchestra.models import Project
from orchestra.models import Task


def completed_projects(projects):
    """
    Filters `projects` queryset to completed ones.
    """
    projects = projects.filter(status=Project.Status.COMPLETED)
    return projects


def incomplete_projects(projects):
    incomplete_project_ids = (
        Task.objects.exclude(Q(status=Task.Status.COMPLETE) |
                             Q(status=Task.Status.ABORTED))
        .values_list('project', flat=True))
    return projects.filter(id__in=incomplete_project_ids)
