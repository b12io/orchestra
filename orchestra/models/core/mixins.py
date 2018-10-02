from pydoc import locate

from django.db.models import Q

from orchestra.core.errors import ModelSaveError
from orchestra.json_schemas.validation import validate_json
from orchestra.json_schemas.tags import TagListSchema


class WorkflowMixin(object):

    def __str__(self):
        return self.slug


class WorkflowVersionMixin(object):

    def __str__(self):
        return '{} - {}'.format(self.workflow.slug, self.slug)


class CertificationMixin(object):

    def __str__(self):
        return '{} - {}'.format(self.slug, self.workflow.slug)


class SanityCheckMixin(object):

    def __str__(self):
        return '{} - {} (created: {}, handled: {})'.format(
            self.project,
            self.check_slug,
            self.created_at,
            self.handled_at)


class StepMixin(object):

    def __str__(self):
        return '{} - {} - {}'.format(self.slug, self.workflow_version.slug,
                                     self.workflow_version.workflow.slug)


class WorkerMixin(object):

    def has_certificate(self, certification, role):
        from orchestra.models import WorkerCertification
        return WorkerCertification.objects.filter(
            worker=self,
            certification=certification,
            role=role
        ).exists()

    def is_reviewer(self, certification):
        from orchestra.models import WorkerCertification
        return self.has_certificate(
            certification,
            WorkerCertification.Role.REVIEWER
        )

    def is_entry_level(self, certification):
        from orchestra.models import WorkerCertification
        return self.has_certificate(
            certification,
            WorkerCertification.Role.ENTRY_LEVEL
        )

    def is_project_admin(self):
        from orchestra.interface_api.project_management.decorators import (
            is_project_admin)
        return is_project_admin(self.user)

    def __str__(self):
        return '{} - @{} -{}'.format(
            self.user.username,
            self.slack_username,
            self.phone
        )

    def formatted_slack_username(self):
        return '<@{}>'.format(self.slack_user_id)


class WorkerCertificationMixin(object):

    def __str__(self):
        return '{} - {} - {} - {} - {}'.format(
            self.worker.user.username, self.certification.slug,
            self.certification.workflow.slug,
            dict(self.TASK_CLASS_CHOICES)[self.task_class],
            dict(self.ROLE_CHOICES)[self.role])

    def save(self, *args, **kwargs):
        if self.role == self.Role.REVIEWER:
            if not (type(self).objects
                    .filter(worker=self.worker, task_class=self.task_class,
                            certification=self.certification,
                            role=self.Role.ENTRY_LEVEL)
                    .exists()):
                raise ModelSaveError('You are trying to add a reviewer '
                                     'certification ({}) for a worker without '
                                     'an entry-level certification'
                                     .format(self))
        super().save(*args, **kwargs)


class ProjectMixin(object):

    def __str__(self):
        return '{} ({})'.format(str(self.workflow_version.slug),
                                self.short_description)


class TaskMixin(object):

    def is_worker_assigned(self, worker):
        """
        Check if specified worker is assigned to the given task.

        Args:
            worker (orchestra.models.Worker):
                The specified worker object.

        Returns:
            worker_assigned_to_task (bool):
                True if worker has existing assignment for the given task.
        """
        return self.assignments.filter(worker=worker).exists()

    def get_detailed_description(self, extra_kwargs=None):
        """
        This function uses a step's `description_function` field to generate
        dynamic text describing a step within a task.
        Args:
            extra_kwargs (dict):
                Additional (dynamic) kwargs that will be passed to the
                description function.
        Returns:
            detailed_description (str):
                Dynamic message describing the task.
        """
        from orchestra.utils.task_lifecycle import (
            get_task_details)
        path = self.step.detailed_description_function.get('path')
        kwargs = self.step.detailed_description_function.get('kwargs', {})
        if extra_kwargs is not None:
            kwargs.update(extra_kwargs)
        try:
            function = locate(path)
            return function(get_task_details(self.id), **kwargs)
        except Exception:
            return ''

    def save(self, *args, **kwargs):
        validate_json('tags', TagListSchema,
                      getattr(self, 'tags', None))
        super().save(*args, **kwargs)

    def __str__(self):
        return '{} - {}'.format(str(self.project), str(self.step.slug))


class TaskAssignmentMixin(object):

    def save(self, *args, **kwargs):
        if self.task.step.is_human:
            if self.worker is None:
                raise ModelSaveError('Worker has to be present '
                                     'if worker type is Human')
        else:
            if self.worker is not None:
                raise ModelSaveError('Worker should not be assigned '
                                     'if worker type is Machine')

        super().save(*args, **kwargs)

    def is_entry_level(self):
        return self.assignment_counter == 0

    def is_reviewer(self):
        return self.assignment_counter > 0

    def __str__(self):
        return '{} - {} - {}'.format(
            str(self.task), self.assignment_counter, str(self.worker))


class TodoMixin(object):

    def __str__(self):
        return '{} - {} ({})'.format(
            self.task,
            self.description,
            self.completed)


class TodoQAMixin(object):

    def __str__(self):
        return '{} - {} ({})'.format(
            self.todo,
            self.comment,
            self.approved)


class TodoListTemplateMixin(object):

    def __str__(self):
        return '{} - {}'.format(
            self.name, self.description)


class PayRateMixin(object):

    def __str__(self):
        return '{} ({} - {})'.format(
            self.worker, self.start_date, self.end_date or 'now')

    def save(self, *args, **kwargs):
        if self.end_date and self.end_date < self.start_date:
            raise ModelSaveError('end_date must be greater than '
                                 'start_date')

        if self.end_date is None:
            # If end_date is None, need to check that no other PayRates have
            # end_date is None, nor do they overlap.
            if type(self).objects.exclude(id=self.id).filter(
                    (Q(end_date__gte=self.start_date) |
                     Q(end_date__isnull=True)),
                    worker=self.worker).exists():
                raise ModelSaveError(
                    'Date range overlaps with existing PayRate entry')
        else:
            # If end_date is not None, need to check if other PayRates overlap.
            if (type(self).objects.exclude(id=self.id).filter(
                    start_date__lte=self.end_date,
                    end_date__isnull=True,
                    worker=self.worker).exists() or
                type(self).objects.exclude(id=self.id).filter(
                    (Q(start_date__lte=self.end_date) &
                     Q(end_date__gte=self.start_date)),
                    worker=self.worker).exists()):
                raise ModelSaveError(
                    'Date range overlaps with existing PayRate entry')
        super().save(*args, **kwargs)
