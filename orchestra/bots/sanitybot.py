from django.utils import timezone
from pydoc import locate

from orchestra.core.errors import SanityBotError
from orchestra.models import Project
from orchestra.models import WorkflowVersion
from orchestra.utils.project_properties import incomplete_projects
from orchestra.utils.notifications import message_experts_slack_group


def _workflow_versions_with_sanity_checks():
    # TODO(marcua): make more specific.
    return WorkflowVersion.objects.all()


def _handle(project, sanity_check, handler):
    handler_type = handler.get('type')
    handler_message = handler.get('message')
    handler_steps = handler.get('steps')
    if (handler_type != 'slack_project_channel' or
            not handler_message or not handler_steps):
        raise SanityBotError('Invalid handler: {}'.format(handler))
    tasks = (
        task for task in project.tasks.all()
        if task.step.slug in handler_steps)
    usernames = {
        assignment.worker.formatted_slack_username()
        for task in tasks
        for assignment in task.assignments.all()
        if assignment and assignment.worker
    }
    message = '{}: {}'.format(' '.join(usernames), handler_message)
    message_experts_slack_group(
        project.slack_group_id, message)


def _handle_sanity_checks(project, sanity_checks, sanity_check_handlers):
    for sanity_check in sanity_checks:
        handlers = sanity_check_handlers.get(sanity_check.check_slug)
        if handlers is None:
            raise SanityBotError(
                'No handlers for {}'.format(sanity_check.check_slug))
        for handler in handlers:
            _handle(project, sanity_check, handler)
        sanity_check.handled_at = timezone.now()
        sanity_check.project = project
        sanity_check.save()


def create_and_handle_sanity_checks():
    workflow_versions = _workflow_versions_with_sanity_checks()
    for project in incomplete_projects(
            Project.objects.filter(
                workflow_version__in=workflow_versions)):
        sanity_checks = project.workflow_version.sanity_checks
        sanity_check_path = (sanity_checks
                             .get('sanity_check_function', {})
                             .get('path'))
        sanity_check_handlers = sanity_checks.get('sanity_check_handlers')
        if sanity_check_path and sanity_check_handlers:
            sanity_check_function = locate(sanity_check_path)
            sanity_checks = sanity_check_function(project)
            _handle_sanity_checks(
                project, sanity_checks, sanity_check_handlers)
