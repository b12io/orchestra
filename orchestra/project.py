from orchestra.google_apps.convenience import create_project_google_folder
from orchestra.models import Project
from orchestra.slack import create_project_slack_group
from orchestra.utils.task_lifecycle import create_subsequent_tasks


def create_project_with_tasks(workflow_slug,
                              description,
                              priority,
                              task_class,
                              project_data,
                              review_document_url):

    project = Project.objects.create(workflow_slug=workflow_slug,
                                     short_description=description,
                                     priority=priority,
                                     project_data=project_data,
                                     task_class=task_class,
                                     review_document_url=review_document_url)

    create_project_slack_group(project)
    create_project_google_folder(project)

    create_subsequent_tasks(project)
    return project
