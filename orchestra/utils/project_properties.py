from django.db.models import Q

from orchestra.models import Project


def completed_projects(projects):
    """
    Filters `projects` queryset to completed ones.
    """
    projects = projects.filter(status=Project.Status.COMPLETED)
    return projects


def incomplete_projects(projects):
    projects = projects.filter(Q(status=Project.Status.ACTIVE) |
                               Q(status=Project.Status.PAUSED))
    return projects
