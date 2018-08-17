from orchestra.models import Project


def completed_projects(projects):
    """
    Filters `projects` queryset to completed ones.
    """
    return projects.filter(status=Project.Status.COMPLETED)
