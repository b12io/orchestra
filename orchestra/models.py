from datetime import datetime
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
    """
    Certifications allow workers to perform different types of tasks.

    Attributes:
        slug (str):
            Unique identifier for the certification.
        name (str):
            Human-readable name for the certification.
        description (str):
            A longer description of the certification.
        required_certifications ([orchestra.models.Certification]):
            Prerequisite certifications for possessing this one.
    """
    slug = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    required_certifications = models.ManyToManyField('self',
                                                     blank=True)

    def __str__(self):
        return '{}'.format(self.slug)


class Worker(models.Model):
    """
    Workers are human experts within the Orchestra ecosystem.

    Attributes:
        user (django.contrib.auth.models.User):
            Django user whom the worker represents.
        start_datetime (datetime.datetime):
            The time the worker was created.
        slack_username (str):
            The worker's Slack username if Slack integration is enabled.
    """
    user = models.OneToOneField(User)
    start_datetime = models.DateTimeField(default=datetime.now)
    slack_username = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return '{}'.format(self.user.username)


class WorkerCertification(models.Model):
    """
    A WorkerCertification maps a worker to a certification they possess.

    Attributes:
        certification (orchestra.models.Certification):
            Certification belonging to the corresponding worker.
        worker (orchestra.models.Worker):
            Worker possessing the given certification.
        task_class (orchestra.models.WorkerCertification.TaskClass):
            Represents whether the worker is in training for the given
            certification or prepared to work on real tasks.
        role (orchestra.models.WorkerCertification.Role):
            Represents whather the worker is an entry-level or review
            worker for the given certification.

    Constraints:
        `certification`, `worker`, `task_class`, and `role` are taken
        to be unique_together.

        Worker must possess an entry-level WorkerCertification before
        obtaining a reviewer one.
    """
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
    """
    A project is a collection of tasks representing a workflow.

    Attributes:
        status (orchestra.models.Project.Status):
            Represents whether the project is being actively worked on.
        workflow_slug (str):
            Identifies the workflow that the project represents.
        start_datetime (datetime.datetime):
            The time the project was created.
        priority (int):
            Represents the relative priority of the project.
        task_class (int):
            Represents whether the project is a worker training exercise
            or a deliverable project.
        review_document_url (str):
            The URL for the review document to be passed between workers
            and reviwers for the project's tasks.
        slack_group_id (str):
            The project's internal Slack group ID if Slack integration
            is enabled.
    """
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
    """
    A task is a cohesive unit of work representing a workflow step.

    Attributes:
        step_slug (str):
            Identifies the step that the project represents.
        project (orchestra.models.Project):
            The project to which the task belongs.
        status (orchestra.models.Task.Status):
            Represents the task's stage within its lifecycle.
    """
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
    """
    A task assignment is a worker's assignment for a given task.

    Attributes:
        start_datetime (datetime.datetime):
            The time the project was created.
        worker (orchestra.models.Worker):
            The worker to whom the given task is assigned.
        task (orchestra.models.Task):
            The given task for the task assignment.
        status (orchestra.models.Project.Status):
            Represents whether the assignment is currently being worked
            on.
        assignment_counter (int):
            Identifies the level of the assignment in the given task's
            review hierarchy (i.e., 0 represents an entry-level worker,
            1 represents the task's first reviewer, etc.).
        in_progress_task_data (str):
            A JSON blob containing the worker's input data for the task
            assignment.
        snapshots (str):
            A JSON blob containing saved snapshots of previous data from
            the task assignment.

    Constraints:
        `task` and `assignment_counter` are taken to be unique_together.

        Task assignments for machine-type tasks cannot have a `worker`,
        while those for human-type tasks must have one.
    """
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
