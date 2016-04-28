from orchestra.google_apps.convenience import create_project_google_folder
from orchestra.models import Project
from orchestra.models import WorkflowVersion
from orchestra.communication.slack import create_project_slack_group
from orchestra.utils.task_lifecycle import create_subsequent_tasks


def create_project_with_tasks(workflow_slug,
                              workflow_version_slug,
                              description,
                              priority,
                              task_class,
                              project_data):

    workflow_version = WorkflowVersion.objects.get(
        slug=workflow_version_slug,
        workflow__slug=workflow_slug)

    project = Project.objects.create(workflow_version=workflow_version,
                                     short_description=description,
                                     priority=priority,
                                     project_data=project_data,
                                     task_class=task_class)

    create_project_slack_group(project)
    create_project_google_folder(project)

    create_subsequent_tasks(project)
    return project
