from django.db.models import Q

from orchestra.models import Project


def completed_projects(projects):
    """
    Filters `projects` queryset to completed ones.
    """
    return projects.filter(status=Project.Status.COMPLETED)


def incomplete_projects(projects):
    return projects.filter(Q(status=Project.Status.ACTIVE) |
                           Q(status=Project.Status.PAUSED))
