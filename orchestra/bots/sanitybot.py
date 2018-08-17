from django.db.models import Max
from django.db.models import Q
from django.utils import timezone
from pydoc import locate

from orchestra.core.errors import SanityBotError
from orchestra.models import Project
from orchestra.models import SanityCheck
from orchestra.models import WorkflowVersion
from orchestra.utils.notifications import message_experts_slack_group


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


def _filter_checks(project, checks, check_configurations):
    latest_check_creation = {
        check['check_slug']: check['max_created_at']
        for check in (SanityCheck.objects
                      .filter(project=project)
                      .values('check_slug')
                      .annotate(max_created_at=Max('created_at')))}
    for check in checks:
        max_created_at = latest_check_creation.get(check.check_slug)
        seconds = (
            check_configurations.get(check.check_slug, {})
            .get('repetition_seconds'))
        now = timezone.now()
        if (max_created_at is None or
                ((seconds is not None) and
                 ((now - max_created_at).total_seconds() > seconds))):
            yield check


def _handle_sanity_checks(project, sanity_checks, check_configurations):
    sanity_checks = _filter_checks(
        project, sanity_checks, check_configurations)
    for sanity_check in sanity_checks:
        config = check_configurations.get(sanity_check.check_slug)
        if config is None:
            raise SanityBotError(
                'No configuration for {}'.format(sanity_check.check_slug))
        handlers = config.get('handlers')
        if handlers is None:
            raise SanityBotError(
                'No handlers for {}'.format(sanity_check.check_slug))
        for handler in handlers:
            _handle(project, sanity_check, handler)
        sanity_check.handled_at = timezone.now()
        sanity_check.project = project
        sanity_check.save()


def create_and_handle_sanity_checks():
    workflow_versions = WorkflowVersion.objects.all()
    incomplete_projects = (Project.objects
                           .filter(workflow_version__in=workflow_versions)
                           .filter(Q(status=Project.Status.ACTIVE) |
                                   Q(status=Project.Status.PAUSED)))

    for project in incomplete_projects:
        sanity_checks = project.workflow_version.sanity_checks
        sanity_check_path = (sanity_checks
                             .get('sanity_check_function', {})
                             .get('path'))
        check_configurations = sanity_checks.get('check_configurations')
        if sanity_check_path and check_configurations:
            sanity_check_function = locate(sanity_check_path)
            sanity_checks = sanity_check_function(project)
            _handle_sanity_checks(
                project, sanity_checks, check_configurations)
