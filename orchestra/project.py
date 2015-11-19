from orchestra.google_apps.convenience import create_project_google_folder
from orchestra.models import Project
from orchestra.models import WorkflowVersion
from orchestra.slack import create_project_slack_group
from orchestra.utils.task_lifecycle import create_subsequent_tasks


def create_project_with_tasks(workflow_slug,
                              description,
                              priority,
                              task_class,
                              project_data,
                              review_document_url,
                              workflow_version_slug=None):

    # Allow backwards compatibility with calls that pass in a version slug in
    # the 'workflow_slug' variable.
    # TODO(dhaas): be less backward-compatible?
    if workflow_version_slug is None:
        try:
            workflow_version = WorkflowVersion.objects.get(slug=workflow_slug)
        except WorkflowVersion.MultipleObjectsReturned:
            raise ValueError('No workflow slug passed, and version slug {} is '
                             'not unique.'.format(workflow_slug))
    else:
        workflow_version = WorkflowVersion.objects.get(
            slug=workflow_version_slug,
            workflow__slug=workflow_slug)

    project = Project.objects.create(workflow_version=workflow_version,
                                     short_description=description,
                                     priority=priority,
                                     project_data=project_data,
                                     task_class=task_class,
                                     review_document_url=review_document_url)

    create_project_slack_group(project)
    create_project_google_folder(project)

    create_subsequent_tasks(project)
    return project
