from django.contrib.auth.models import User
from django.db import models
from djmoney.models.fields import MoneyField
from django.utils import timezone
from jsonfield import JSONField

from orchestra.core.errors import ModelSaveError
from orchestra.utils.assignment_snapshots import load_snapshots

# TODO(marcua): Convert ManyToManyFields to django-hstore referencefields or
# wait for django-postgres ArrayFields in Django 1.8.


class Workflow(models.Model):
    """
    Workflows describe the steps and requirements for experts to complete work.

    This model represents workflows that have been loaded into the database and
    are usable by Orchestra projects. All workflows are also defined in the
    codebase (see the `code_directory` attribute).

    Attributes:
        slug (str):
            Unique identifier for the workflow.
        name (str):
            Human-readable name for the workflow.
        description (str):
            A longer description of the workflow.
        code_directory (str):
            The full path to the location of the workflow's manifest.
    """
    created_at = models.DateTimeField(default=timezone.now)
    slug = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    code_directory = models.CharField(max_length=255, unique=True)
    sample_data_load_function = JSONField(default={})

    class Meta:
        app_label = 'orchestra'

    def __str__(self):
        return self.slug


class WorkflowVersion(models.Model):
    """
    WorkflowVersions represent changes made to a single workflow over time.

    Attributes:
        slug (str):
            Unique identifier for the workflow version.
        name (str):
            Human-readable name for the workflow version.
        description (str):
            A longer description of the workflow version.
        workflow (orchestra.models.Workflow):
            The workflow that this is a version of.
    """
    created_at = models.DateTimeField(default=timezone.now)
    slug = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    description = models.TextField()
    workflow = models.ForeignKey(Workflow, related_name='versions')

    class Meta:
        app_label = 'orchestra'
        unique_together = (('workflow', 'slug'),)

    def __str__(self):
        return '{} - {}'.format(self.workflow.slug, self.slug)


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
        workflow (orchestra.models.Workflow):
            The workflow the certification is scoped to.
    """
    created_at = models.DateTimeField(default=timezone.now)
    slug = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    description = models.TextField()
    required_certifications = models.ManyToManyField(
        'self',
        blank=True,
        related_name='dependent_certifications',
        symmetrical=False)
    workflow = models.ForeignKey(Workflow, related_name='certifications')

    def __str__(self):
        return '{} - {}'.format(self.slug, self.workflow.slug)

    class Meta:
        app_label = 'orchestra'
        unique_together = (('workflow', 'slug'),)


class Step(models.Model):
    """
    Steps represent individual tasks in a workflow version.

    Attributes:
        slug (str):
            Unique identifier for the workflow step.
        name (str):
            Human-readable name for the workflow step.
        description (str):
            A longer description of the workflow step.
        workflow_version (orchestra.models.WorkflowVersion):
            The workflow version that this is a step of.
        creation_depends_on ([orchestra.models.Step]):
            Workflow steps that must be complete to begin this step.
        submission_depends_on ([orchestra.models.Step]):
            Workflow steps that must be complete to end this step.
        is_human (bool):
            False if this step is performed by a machine.
        execution_function (str):
            A JSON blob containing the path to and name of a python method that
            will execute this step (only valid for machine steps).
        required_certifications ([orchestra.models.Certification]):
            The certifications a worker must have in order to work on this step
            (only valid for human steps).
        assignment_policy (str):
            A JSON blob used to decide which worker to assign to this step
            (only valid for human steps).
        review_policy (str):
            A JSON blob used to decide whether or not to review this step
            (only valid for human steps).
        user_interface (str):
            A JSON blob used to describe the files used in the user interface
            for this step (only valid for human steps).
    """
    # General fields
    created_at = models.DateTimeField(default=timezone.now)
    slug = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    description = models.TextField()
    workflow_version = models.ForeignKey(WorkflowVersion, related_name='steps')
    creation_depends_on = models.ManyToManyField(
        'self',
        blank=True,
        related_name='creation_dependents',
        symmetrical=False)
    submission_depends_on = models.ManyToManyField(
        'self',
        blank=True,
        related_name='submission_dependents',
        symmetrical=False)

    # Machine step fields
    is_human = models.BooleanField()
    execution_function = JSONField(default={})

    # Human step fields
    required_certifications = models.ManyToManyField(Certification, blank=True)
    assignment_policy = JSONField(default={})
    review_policy = JSONField(default={})
    user_interface = JSONField(default={})

    class Meta:
        app_label = 'orchestra'
        unique_together = (('workflow_version', 'slug'),)

    def __str__(self):
        return '{} - {} - {}'.format(self.slug, self.workflow_version.slug,
                                     self.workflow_version.workflow.slug)


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
    start_datetime = models.DateTimeField(default=timezone.now)
    slack_username = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return '{}'.format(self.user.username)

    class Meta:
        app_label = 'orchestra'


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
        app_label = 'orchestra'
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

    created_at = models.DateTimeField(default=timezone.now)
    certification = models.ForeignKey(Certification)
    worker = models.ForeignKey(Worker, related_name='certifications')
    task_class = models.IntegerField(choices=TASK_CLASS_CHOICES)
    role = models.IntegerField(choices=ROLE_CHOICES)

    def __str__(self):
        return '{} - {} - {} - {} - {}'.format(
            self.worker.user.username, self.certification.slug,
            self.certification.workflow.slug,
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
        super().save(*args, **kwargs)


class Project(models.Model):
    """
    A project is a collection of tasks representing a workflow.

    Attributes:
        start_datetime (datetime.datetime):
            The time the project was created.
        status (orchestra.models.Project.Status):
            Represents whether the project is being actively worked on.
        workflow_version (orchestra.models.WorkflowVersion):
            Identifies the workflow that the project follows.
        priority (int):
            Represents the relative priority of the project.
        task_class (int):
            Represents whether the project is a worker training exercise
            or a deliverable project.
        team_messages_url (str):
            A scratchpad in which teammates can collaborate, created only if
            Google Apps support is turned on.
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

    start_datetime = models.DateTimeField(default=timezone.now)
    status = models.IntegerField(choices=STATUS_CHOICES,
                                 default=Status.ACTIVE)

    workflow_version = models.ForeignKey(WorkflowVersion,
                                         related_name='projects')

    short_description = models.TextField()
    priority = models.IntegerField()
    project_data = JSONField(default={}, blank=True)
    task_class = models.IntegerField(
        choices=WorkerCertification.TASK_CLASS_CHOICES)
    team_messages_url = models.URLField(null=True, blank=True)
    slack_group_id = models.CharField(max_length=200, null=True, blank=True)

    def __str__(self):
        return '{} ({})'.format(str(self.workflow_version.slug),
                                self.short_description)

    class Meta:
        app_label = 'orchestra'


class Task(models.Model):
    """
    A task is a cohesive unit of work representing a workflow step.

    Attributes:
        start_datetime (datetime.datetime):
            The time the Task was created.
        step (orchestra.models.Step):
            Identifies the step that the task represents.
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

    start_datetime = models.DateTimeField(default=timezone.now)
    step = models.ForeignKey(Step, related_name='tasks')
    project = models.ForeignKey(Project, related_name='tasks')
    status = models.IntegerField(choices=STATUS_CHOICES)

    def __str__(self):
        return '{} - {}'.format(str(self.project), str(self.step.slug))

    class Meta:
        app_label = 'orchestra'


class TaskAssignment(models.Model):
    """
    A task assignment is a worker's assignment for a given task.

    Attributes:
        start_datetime (datetime.datetime):
            The time the task was assigned for this iteration.
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
        app_label = 'orchestra'
        unique_together = ('task', 'assignment_counter')

    class SnapshotType:
        SUBMIT = 0
        ACCEPT = 1
        REJECT = 2

    class Status:
        PROCESSING = 0
        SUBMITTED = 1
        FAILED = 2

    STATUS_CHOICES = (
        (Status.PROCESSING, 'Processing'),
        (Status.SUBMITTED, 'Submitted'),
        (Status.FAILED, 'Failed'))

    start_datetime = models.DateTimeField(default=timezone.now)
    worker = models.ForeignKey(Worker,
                               null=True,
                               blank=True)
    task = models.ForeignKey(Task, related_name='assignments')

    status = models.IntegerField(choices=STATUS_CHOICES)

    # Counter of a worker assigned to the task
    assignment_counter = models.IntegerField(default=0)

    # Opaque field that stores current state of task as per the Step's
    # description
    in_progress_task_data = JSONField(default={}, blank=True)

    # When a worker submits, accepts, or rejects a task, we snapshot their
    # in_workflow_task_data along with the date in the following format:
    # {'snapshots': [
    #   {'data': snapshotted_task_data,
    #    'datetime': ISO 8601 datetime in UTC time,
    #    'work_time_seconds': integer seconds,
    #    'type': value from SnapshotType}]
    #  '__version': 1}
    snapshots = JSONField(default={}, blank=True)

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

    def __str__(self):
        return '{} - {} - {}'.format(
            str(self.task), self.assignment_counter, str(self.worker))


class Iteration(models.Model):
    """
    Iterations are the contiguous units of a worker's time on task.

    Attributes:
        start_datetime (datetime.datetime):
            The time the task was assigned for this iteration.
        end_datetime (datetime.datetime):
            The time the iteration was completed. Will be None if the iteration
            is currently in progress.
        assignment (orchestra.models.TaskAssigment):
            The task assignment to which the iteration belongs.
        status (orchestra.models.Iteration.Action):
            Represents the status of the iteration. `REQUESTED_REVIEW` means
            that the task was moved up the review hierarchy, while
            `PROVIDED_REVIEW` indicates that it was moved back down.
        submitted_data (str):
            A JSON blob containing submitted data for this iteration. Will be
            None if the iteration is currently in progress.
    """

    class Status:
        PROCESSING = 0
        REQUESTED_REVIEW = 1
        PROVIDED_REVIEW = 2

    STATUS_CHOICES = (
        (Status.PROCESSING, 'Processing'),
        (Status.REQUESTED_REVIEW, 'Requested Review'),
        (Status.PROVIDED_REVIEW, 'Provided Review'))

    start_datetime = models.DateTimeField(default=timezone.now)
    end_datetime = models.DateTimeField(null=True, blank=True)
    assignment = models.ForeignKey(TaskAssignment, related_name='iterations')
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=Status.PROCESSING)
    submitted_data = JSONField(default={}, blank=True)


class TimeEntry(models.Model):
    """
    A time entry is a record of time worked on a given task assignment.

    Attributes:
        date (datetime.date):
            The date the work was done.
        time_worked (datetime.timedelta):
            Amount of time worked.
        worker (orchestra.models.Worker):
            The worker for whom the timer is tracking work.
        assignment (orchestra.models.TaskAssignment): optional
            The task assignment for which the work was done.
        description (str): optional
            Brief description of the work done.
        timer_start_time (datetime.datetime): optional
            Server timestamp for timer start (not null if TimeEntry is
            created using work timer)
        timer_stop_time (datetime.datetime): optional
            Server timestamp for timer stop (not null if TimeEntry is
            created using work timer)
    """
    date = models.DateField()
    time_worked = models.DurationField()
    # TODO(lydia): Drop null=True after a data migration to fill in workers.
    worker = models.ForeignKey(Worker, related_name='time_entries',
                               null=True)
    assignment = models.ForeignKey(TaskAssignment,
                                   related_name='time_entries',
                                   null=True)
    description = models.CharField(max_length=200, null=True, blank=True)
    timer_start_time = models.DateTimeField(null=True)
    timer_stop_time = models.DateTimeField(null=True)
    is_deleted = models.BooleanField(default=False)


class TaskTimer(models.Model):
    """
    A task timer is an object used to implement a work timer. It must be
    associated with a worker, and can optionally be associated with a specific
    TaskAssignment. A worker can only have one task timer object associated.

    Attributes:
        worker (orchestra.models.Worker):
            The worker for whom the timer is tracking work.
        assignment (orchestra.models.TaskAssignment): optional
            The task assignment for which the timer is tracking work.
        start_time (datetime.datetime): optional
            Server timestamp for timer start.
        stop_time (datetime.datetime): optional
            Server timestamp for timer stop.
    """
    worker = models.OneToOneField(Worker, related_name='timer')
    assignment = models.ForeignKey(TaskAssignment,
                                   related_name='timers',
                                   null=True)
    start_time = models.DateTimeField(null=True)
    stop_time = models.DateTimeField(null=True)


class PayRate(models.Model):
    """
    A PayRate object tracks how much a worker is paid over time.

    Attributes:
        worker (orchestra.models.Worker):
            The worker who is being paid.
        hourly_rate (djmoney.models.fields.MoneyPatched):
            The amount of money the worker receives per hour.
        hourly_multiplier (decimal.Decimal):
            Any multiplier that gets applied to a worker's pay
            (e.g., fees imposed by a payment gateway).
        start_datetime (datetime.datetime):
            The beginning of the time period of the pay rate.
        end_datetime (datetime.datetime):
            The end of the time period of the pay rate,
            or None if it's the current period.
    """
    worker = models.ForeignKey(Worker, related_name='pay_rates')
    hourly_rate = MoneyField(
        max_digits=10, decimal_places=2, default_currency='USD')
    hourly_multiplier = models.DecimalField(max_digits=6, decimal_places=4)
    start_datetime = models.DateTimeField(default=timezone.now)
    end_datetime = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return '{} ({} - {})'.format(
            self.worker, self.start_datetime, self.end_datetime or 'now')


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
