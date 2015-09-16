from django.contrib.auth.models import User
from django.db import models
from jsonfield import JSONField

from orchestra.core.errors import ModelSaveError
from orchestra.workflow import get_workflow_choices
from orchestra.workflow import get_step_choices
from orchestra.workflow import get_workflow_by_slug
from orchestra.workflow import Step
from orchestra.utils.assignment_snapshots import load_snapshots


# TODO(marcua): Convert ManyToManyFields to django-hstore referencefields or
# wait for django-postgres ArrayFields in Django 1.8.


class Certification(models.Model):
    slug = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    required_certifications = models.ManyToManyField('self',
                                                     blank=True)

    def __str__(self):
        return '{}'.format(self.slug)


class Worker(models.Model):
    user = models.OneToOneField(User)
    start_datetime = models.DateTimeField(auto_now_add=True)
    slack_username = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return '{}'.format(self.user.username)


class WorkerCertification(models.Model):

    class Meta:
        unique_together = ('certification', 'worker', 'task_class', 'role')

    class TaskClass:
        TRAINING = 0
        REAL = 1

    TASK_CLASS_CHOICES = (
        (TaskClass.TRAINING, 'Training tasks'),
        (TaskClass.REAL, 'A real task'))

    # If a worker has a REVIEWER certification, then they must have
    # an ENTRY_LEVEL certification
    class Role:
        ENTRY_LEVEL = 0
        REVIEWER = 1

    ROLE_CHOICES = (
        (Role.ENTRY_LEVEL, 'Entry-level'),
        (Role.REVIEWER, 'Reviewer'))

    certification = models.ForeignKey(Certification)
    worker = models.ForeignKey(Worker, related_name='certifications')
    task_class = models.IntegerField(choices=TASK_CLASS_CHOICES)
    role = models.IntegerField(choices=ROLE_CHOICES)

    def __str__(self):
        return '{} - {} - {} - {}'.format(
            self.worker.user.username, self.certification.slug,
            dict(WorkerCertification.TASK_CLASS_CHOICES)[self.task_class],
            dict(WorkerCertification.ROLE_CHOICES)[self.role])

    def save(self, *args, **kwargs):
        if self.role == WorkerCertification.Role.REVIEWER:
            if not (WorkerCertification.objects
                    .filter(worker=self.worker, task_class=self.task_class,
                            certification=self.certification,
                            role=WorkerCertification.Role.ENTRY_LEVEL)
                    .exists()):
                raise ModelSaveError('You are trying to add a reviewer '
                                     'certification ({}) for a worker without '
                                     'an entry-level certification'
                                     .format(self))
        super(WorkerCertification, self).save(*args, **kwargs)


class Project(models.Model):
    class Status:
        ACTIVE = 0
        ABORTED = 2

    STATUS_CHOICES = (
        (Status.ACTIVE, 'Active'),
        (Status.ABORTED, 'Aborted'))

    status = models.IntegerField(choices=STATUS_CHOICES,
                                 default=Status.ACTIVE)

    workflow_slug = models.CharField(max_length=200,
                                     choices=get_workflow_choices())

    short_description = models.TextField()
    start_datetime = models.DateTimeField(auto_now_add=True)
    priority = models.IntegerField()
    project_data = JSONField(default={})
    task_class = models.IntegerField(
        choices=WorkerCertification.TASK_CLASS_CHOICES)
    review_document_url = models.URLField(null=True, blank=True)
    slack_group_id = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return '{} ({})'.format(str(self.workflow_slug),
                                self.short_description)


class Task(models.Model):
    class Status:
        AWAITING_PROCESSING = 0
        PROCESSING = 1
        PENDING_REVIEW = 2
        REVIEWING = 3
        POST_REVIEW_PROCESSING = 4
        COMPLETE = 5
        ABORTED = 6

    STATUS_CHOICES = (
        (Status.AWAITING_PROCESSING, 'Awaiting Processing'),
        (Status.PROCESSING, 'Processing'),
        (Status.PENDING_REVIEW, 'Pending Review'),
        (Status.REVIEWING, 'Reviewing'),
        (Status.POST_REVIEW_PROCESSING, 'Post-review Processing'),
        (Status.ABORTED, 'Aborted'),
        (Status.COMPLETE, 'Complete'))

    step_slug = models.CharField(max_length=200,
                                 choices=get_step_choices())
    project = models.ForeignKey(Project, related_name='tasks')
    status = models.IntegerField(choices=STATUS_CHOICES)

    def __str__(self):
        return '{} - {}'.format(str(self.project), str(self.step_slug))


class TaskAssignment(models.Model):

    class Meta:
        unique_together = ('task', 'assignment_counter')

    class SnapshotType:
        SUBMIT = 0
        ACCEPT = 1
        REJECT = 2

    class Status:
        PROCESSING = 0
        SUBMITTED = 1

    STATUS_CHOICES = (
        (Status.PROCESSING, 'Processing'),
        (Status.SUBMITTED, 'Submitted'))

    start_datetime = models.DateTimeField(auto_now_add=True)
    worker = models.ForeignKey(Worker,
                               null=True,
                               blank=True)
    task = models.ForeignKey(Task, related_name='assignments')

    status = models.IntegerField(choices=STATUS_CHOICES)

    # Counter of a worker assigned to the task
    assignment_counter = models.IntegerField(default=0)

    # Opaque field that stores current state of task as per the Step's
    # description
    in_progress_task_data = JSONField()

    # When a worker submits, accepts, or rejects a task, we snapshot their
    # in_workflow_task_data along with the date in the following format:
    # {'snapshots': [
    #   {'data': snapshotted_task_data,
    #    'datetime': ISO 8601 datetime in UTC time,
    #    'work_time_seconds': integer seconds,
    #    'type': value from SnapshotType}]
    #  '__version': 1}
    snapshots = JSONField()

    def save(self, *args, **kwargs):
        workflow = get_workflow_by_slug(self.task.project.workflow_slug)
        step = workflow.get_step(self.task.step_slug)
        if step.worker_type == Step.WorkerType.HUMAN:
            if self.worker is None:
                raise ModelSaveError('Worker has to be present '
                                     'if worker type is Human')
        else:
            if self.worker is not None:
                raise ModelSaveError('Worker should not be assigned '
                                     'if worker type is Machine')

        super(TaskAssignment, self).save(*args, **kwargs)


# Attach a post-init signal to TaskAssigment.  Every
# TaskAssignment that gets constructed will now call
# this post-init signal after loading from the database
# (or memory).  We run `load_snapshots` after loading from
# the database so that we can migrate old JSON task assignment
# snapshots.
def task_assignment_post_init(sender, instance, **kwargs):
    instance.snapshots = load_snapshots(instance.snapshots)
models.signals.post_init.connect(
    task_assignment_post_init, sender=TaskAssignment)
