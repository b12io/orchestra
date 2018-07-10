from django.conf import settings
from django.db import models
from django.utils import timezone
from djmoney.models.fields import MoneyField
from jsonfield import JSONField
from phonenumber_field.modelfields import PhoneNumberField
from orchestra.models.core.mixins import CertificationMixin
from orchestra.models.core.mixins import TodoListTemplateMixin
from orchestra.models.core.mixins import PayRateMixin
from orchestra.models.core.mixins import ProjectMixin
from orchestra.models.core.mixins import StepMixin
from orchestra.models.core.mixins import SanityCheckMixin
from orchestra.models.core.mixins import TaskAssignmentMixin
from orchestra.models.core.mixins import TaskMixin
from orchestra.models.core.mixins import TodoMixin
from orchestra.models.core.mixins import TodoQAMixin
from orchestra.models.core.mixins import WorkerCertificationMixin
from orchestra.models.core.mixins import WorkerMixin
from orchestra.models.core.mixins import WorkflowMixin
from orchestra.models.core.mixins import WorkflowVersionMixin
from orchestra.utils.models import BaseModel

# TODO(marcua): Convert ManyToManyFields to django-hstore referencefields or
# wait for django-postgres ArrayFields in Django 1.8.


class Workflow(WorkflowMixin, models.Model):
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


class WorkflowVersion(WorkflowVersionMixin, models.Model):
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
        sanity_checks (str):
            A JSON blob used to define the sanity checks we run.
            An example configuration can be found in
            `orchestra.tests.helpers.workflow.py` in the
            `sanitybot_workflow` configuration.
    """
    created_at = models.DateTimeField(default=timezone.now)
    slug = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    description = models.TextField()
    workflow = models.ForeignKey(
        Workflow, related_name='versions', on_delete=models.CASCADE)
    sanity_checks = JSONField(default={})

    class Meta:
        app_label = 'orchestra'
        unique_together = (('workflow', 'slug'),)


class Certification(CertificationMixin, models.Model):
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
    workflow = models.ForeignKey(
        Workflow, related_name='certifications', on_delete=models.CASCADE)

    class Meta:
        app_label = 'orchestra'
        unique_together = (('workflow', 'slug'),)


class Step(StepMixin, models.Model):
    """
    Steps represent individual tasks in a workflow version.

    Attributes:
        slug (str):
            Unique identifier for the workflow step.
        name (str):
            Human-readable name for the workflow step.
        description (str):
            A longer description of the workflow step.
        detailed_description_function (str):
            A JSON blob used to give a dynamic description of the step.
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
        creation_policy (str):
            A JSON blob used to describe if the task should be created,
            allowing tasks to conditionally be created.
        user_interface (str):
            A JSON blob used to describe the files used in the user interface
            for this step (only valid for human steps).
    """
    # General fields
    created_at = models.DateTimeField(default=timezone.now)
    slug = models.CharField(max_length=200)
    name = models.CharField(max_length=200)
    description = models.TextField()
    detailed_description_function = JSONField(default={})
    workflow_version = models.ForeignKey(
        WorkflowVersion, related_name='steps', on_delete=models.CASCADE)
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
    creation_policy = JSONField(default={})
    user_interface = JSONField(default={})

    class Meta:
        app_label = 'orchestra'
        unique_together = (('workflow_version', 'slug'),)


class Worker(WorkerMixin, models.Model):
    """
    Workers are human experts within the Orchestra ecosystem.

    Attributes:
        user (django.contrib.auth.models.User):
            Django user whom the worker represents.
        start_datetime (datetime.datetime):
            The time the worker was created.
        slack_username (str):
            The worker's Slack username if Slack integration is enabled.
        slack_user_id (str):
            The worker's Slack id if Slack integration is enabled.
        phone (str):
            The worker's phone number
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    start_datetime = models.DateTimeField(default=timezone.now)
    slack_username = models.CharField(max_length=200, blank=True, null=True)
    slack_user_id = models.CharField(max_length=200, blank=True, null=True)
    phone = PhoneNumberField(null=True)

    class Meta:
        app_label = 'orchestra'


class WorkerCertification(WorkerCertificationMixin, models.Model):
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
        staffbot_enabled (bool):
            Whether the Worker's certification should trigger
            StaffBot's inquiried for this Worker.
        staffing_priority (int):
            The worker's priority when new tasks are being staffed by
            tools like StaffBot.

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
    certification = models.ForeignKey(Certification, on_delete=models.CASCADE)
    worker = models.ForeignKey(
        Worker, related_name='certifications', on_delete=models.CASCADE)
    task_class = models.IntegerField(choices=TASK_CLASS_CHOICES)
    role = models.IntegerField(choices=ROLE_CHOICES)
    staffbot_enabled = models.BooleanField(default=True)
    staffing_priority = models.IntegerField(default=0)


class Project(ProjectMixin, models.Model):
    """
    A project is a collection of tasks representing a workflow.

    Attributes:
        start_datetime (datetime.datetime):
            The time the project was created.
        status (orchestra.models.Project.Status):
            Represents whether the project is being actively worked on.
        workflow_version (orchestra.models.WorkflowVersion):
            Identifies the workflow that the project follows.
        short_description(str):
            A short description of the project.
        priority (int):
            Represents the relative priority of the project.
        project_data (str):
            A JSON blob used to describe the project_data.
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
                                         on_delete=models.CASCADE,
                                         related_name='projects')

    short_description = models.TextField()
    priority = models.IntegerField()
    project_data = JSONField(default={}, blank=True)
    task_class = models.IntegerField(
        choices=WorkerCertification.TASK_CLASS_CHOICES)
    team_messages_url = models.URLField(null=True, blank=True)
    slack_group_id = models.CharField(max_length=200, null=True, blank=True)

    class Meta:
        app_label = 'orchestra'


class Task(TaskMixin, models.Model):
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
    step = models.ForeignKey(Step, related_name='tasks',
                             on_delete=models.CASCADE)
    project = models.ForeignKey(
        Project, related_name='tasks', on_delete=models.CASCADE)
    status = models.IntegerField(choices=STATUS_CHOICES)

    class Meta:
        app_label = 'orchestra'


class TaskAssignment(TaskAssignmentMixin, BaseModel):
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

    Constraints:
        `task` and `assignment_counter` are taken to be unique_together.

        Task assignments for machine-type tasks cannot have a `worker`,
        while those for human-type tasks must have one.
    """
    class Meta:
        app_label = 'orchestra'
        # TODO(marcua): Bring back this uniqueness/integrity
        # constraint once we can delete task assignments (marked as
        # `is_deleted=True`) and have new undeleted ones still be
        # considered unique.
        # unique_together = ('task', 'assignment_counter')

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
                               related_name='assignments',
                               on_delete=models.CASCADE,
                               null=True,
                               blank=True)
    task = models.ForeignKey(
        Task, related_name='assignments', on_delete=models.CASCADE)

    status = models.IntegerField(choices=STATUS_CHOICES)

    # Counter of a worker assigned to the task
    assignment_counter = models.IntegerField(default=0)

    # Opaque field that stores current state of task as per the Step's
    # description
    in_progress_task_data = JSONField(default={}, blank=True)


class Iteration(BaseModel):
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
    assignment = models.ForeignKey(
        TaskAssignment, related_name='iterations', on_delete=models.CASCADE)
    status = models.IntegerField(
        choices=STATUS_CHOICES, default=Status.PROCESSING)
    submitted_data = JSONField(default={}, blank=True)


class TimeEntry(BaseModel):
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
    class Meta:
        verbose_name_plural = 'time entries'

    date = models.DateField()
    time_worked = models.DurationField()
    worker = models.ForeignKey(
        Worker, related_name='time_entries', on_delete=models.CASCADE)
    assignment = models.ForeignKey(TaskAssignment,
                                   on_delete=models.CASCADE,
                                   related_name='time_entries',
                                   null=True)
    description = models.CharField(max_length=200, null=True, blank=True)
    timer_start_time = models.DateTimeField(null=True)
    timer_stop_time = models.DateTimeField(null=True)


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
        description (str): optional
            Description of currently ongoing work.
    """
    worker = models.OneToOneField(
        Worker, related_name='timer', on_delete=models.CASCADE)
    assignment = models.ForeignKey(TaskAssignment,
                                   on_delete=models.CASCADE,
                                   related_name='timers',
                                   null=True)
    start_time = models.DateTimeField(null=True)
    stop_time = models.DateTimeField(null=True)
    description = models.CharField(max_length=200, null=True, blank=True)


class PayRate(PayRateMixin, models.Model):
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
        start_date (datetime.date):
            The beginning of the time period of the pay rate (inclusive).
        end_date (datetime.date):
            The end of the time period of the pay rate (inclusive),
            or None if it's the current period.
    """
    worker = models.ForeignKey(
        Worker, related_name='pay_rates', on_delete=models.CASCADE)
    hourly_rate = MoneyField(
        max_digits=10, decimal_places=2, default_currency='USD')
    hourly_multiplier = models.DecimalField(max_digits=6, decimal_places=4)
    start_date = models.DateField(default=timezone.now)
    end_date = models.DateField(null=True, blank=True)


class TodoListTemplate (TodoListTemplateMixin, BaseModel):
    """
    A todo template

    Attributes:
        slug (str):
            A unique key for the todo list
        name (str):
            A human-readable name for the todo list template
        description (str):
            A longer description of the todo list template
        creator (orchestra.models.Worker)
            The worker who created the todo list template. This field is null
            if it is generated by the system.
        todos (str)
            A JSON blob that describe the todos in the todo list template.
        conditional_property_function (str)
            A JSON blob containing the path to and name of a python method
            that will return the preconditions to prune the created todos.
    """
    class Meta:
        app_label = 'orchestra'

    slug = models.CharField(max_length=200, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField()
    creator = models.ForeignKey(
        Worker, null=True, blank=True,
        related_name='creator', on_delete=models.SET_NULL)
    todos = JSONField(default={'items': []})
    conditional_property_function = JSONField(default={})


class Todo(TodoMixin, BaseModel):
    """
    A todo on a task.

    Attributes:
        task (orchestra.models.Task):
            The given task the Todo is attached to.
        completed (boolean):
            Whether the todo has been completed.
        description (str):
            A text description of the Todo.
        start_by_datetime (datetime.datetime):
            The time to start the todo. (inclusive)
        due_datetime (datetime.datetime):
            The time the todo is due
        skipped_datetime (datetime.datetime):
            The time the todo was skipped
        parent_todo (orchestra.models.Todo):
            The parent todo item
        template (orchestra.models.TodoListTemplate)
            The template the todo is based on
        activity_log (str)
            A JSON blob that records the user actions
            with this todo


    Constraints:
        `task` and `assignment_counter` are taken to be unique_together.

        Task assignments for machine-type tasks cannot have a `worker`,
        while those for human-type tasks must have one.
    """
    class Meta:
        app_label = 'orchestra'

    task = models.ForeignKey(
        Task, related_name='todos', on_delete=models.CASCADE)
    description = models.TextField()
    completed = models.BooleanField(default=False)
    start_by_datetime = models.DateTimeField(null=True, blank=True)
    due_datetime = models.DateTimeField(null=True, blank=True)
    skipped_datetime = models.DateTimeField(null=True, blank=True)
    parent_todo = models.ForeignKey(
        'self', null=True, related_name='parent', on_delete=models.CASCADE)
    template = models.ForeignKey(
        TodoListTemplate, null=True, blank=True, related_name='template',
        on_delete=models.SET_NULL)
    activity_log = JSONField(default={'actions': []})


class TodoQA(TodoQAMixin, BaseModel):
    """
    A QA check for a todo on a task.

    Attributes:
        todo (orchestra.models.Todo):
            The given todo for which QA is done.
        approved (boolean):
            Whether the todo has been approved or not.
        comment (str):
            A text description explaining why a todo was
            approved or disapproved.

    Constraints:
        `todo` has to be unique.
    """
    class Meta:
        app_label = 'orchestra'

    todo = models.OneToOneField(
        Todo, related_name='qa', on_delete=models.CASCADE)
    comment = models.TextField(null=True, blank=True)
    approved = models.NullBooleanField(blank=True)


class SanityCheck(SanityCheckMixin, BaseModel):
    """
    A sanity check that SanityBot raises on a project.

    Attributes:
        project (orchestra.models.Project):
            The project for which the sanity check is raised.
        handled_at (boolean):
            When the sanity check was handled (e.g., messaging a team member).
        check_slug (str):
            A project-specific slug describing the sanity check.
    """
    class Meta:
        app_label = 'orchestra'

    project = models.ForeignKey(
        Project, related_name='sanity_checks', on_delete=models.CASCADE)
    handled_at = models.DateTimeField(blank=True, null=True)
    check_slug = models.CharField(max_length=200)
