from datetime import timedelta
from dateutil.parser import parse
from unittest.mock import patch

import factory
from django.contrib.auth.models import User
from django.test import Client
from django.test import override_settings
from django.utils import timezone

from orchestra.models import CommunicationPreference
from orchestra.models import Iteration
from orchestra.models import StaffBotRequest
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse
from orchestra.models import Step
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import WorkerCertification
from orchestra.models import Workflow
from orchestra.models import WorkflowVersion
from orchestra.communication.slack import create_project_slack_group
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import submit_task
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import current_assignment
from orchestra.utils.task_properties import get_iteration_history
from orchestra.tests.helpers.iterations import verify_iterations
from orchestra.tests.helpers.workflow import workflow_fixtures
from orchestra.workflow.defaults import get_default_assignment_policy
from orchestra.workflow.defaults import get_default_review_policy

BASE_DATETIME = parse('2015-10-12T00:00:00+00:00')
ITERATION_DURATION = timedelta(hours=1)
PICKUP_DELAY = timedelta(hours=1)


def get_detailed_description(task_details, text=None):
    if text is None:
        text = 'No text given'
    return '{} {}'.format(text, task_details['step']['slug'])


class WorkflowFactory(factory.django.DjangoModelFactory):

    code_directory = factory.Sequence(
        lambda n: 'Code Directory {}'.format(n))
    slug = factory.Sequence(
        lambda n: 'Slug {}'.format(n))

    class Meta:
        model = Workflow


class WorkflowVersionFactory(factory.django.DjangoModelFactory):

    workflow = factory.SubFactory(WorkflowFactory)

    class Meta:
        model = WorkflowVersion


class StepFactory(factory.django.DjangoModelFactory):

    is_human = False
    workflow_version = factory.SubFactory(WorkflowVersionFactory)

    class Meta:
        model = Step


class UserFactory(factory.django.DjangoModelFactory):
    username = factory.Sequence(
        lambda n: 'Username {}'.format(n))

    class Meta:
        model = User

    password = factory.PostGenerationMethodCall('set_password',
                                                'defaultpassword')


class WorkerFactory(factory.django.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = 'orchestra.Worker'


class CertificationFactory(factory.django.DjangoModelFactory):

    slug = factory.Sequence(
        lambda n: 'Slug {}'.format(n))
    name = factory.Sequence(
        lambda n: 'Name {}'.format(n))
    description = factory.Sequence(
        lambda n: 'Description {}'.format(n))
    workflow = factory.SubFactory(WorkflowFactory)

    class Meta:
        model = 'orchestra.Certification'


class WorkerCertificationFactory(factory.django.DjangoModelFactory):
    certification = factory.SubFactory(CertificationFactory)
    worker = factory.SubFactory(WorkerFactory)
    task_class = WorkerCertification.TaskClass.REAL
    role = WorkerCertification.Role.ENTRY_LEVEL

    class Meta:
        model = 'orchestra.WorkerCertification'


class PayRateFactory(factory.django.DjangoModelFactory):
    worker = factory.SubFactory(WorkerFactory)
    hourly_multiplier = 1

    class Meta:
        model = 'orchestra.PayRate'


class ProjectFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'orchestra.Project'

    workflow_version = factory.SubFactory(WorkflowVersionFactory)
    short_description = factory.Sequence(
        lambda n: 'Project {}'.format(n))
    priority = 0
    task_class = WorkerCertification.TaskClass.REAL


class TaskFactory(factory.django.DjangoModelFactory):

    step = factory.SubFactory(StepFactory)
    project = factory.SubFactory(ProjectFactory)
    status = Task.Status.AWAITING_PROCESSING

    class Meta:
        model = 'orchestra.Task'


class TaskAssignmentFactory(factory.django.DjangoModelFactory):
    task = factory.SubFactory(TaskFactory)
    status = TaskAssignment.Status.PROCESSING

    class Meta:
        model = 'orchestra.TaskAssignment'


class TimeEntryFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'orchestra.TimeEntry'


class CommunicationPreferenceFactory(factory.django.DjangoModelFactory):

    worker = factory.SubFactory(WorkerFactory)
    communication_type = (CommunicationPreference.CommunicationType.
                          TASK_STATUS_CHANGE.value)
    methods = CommunicationPreference.get_default_methods()

    class Meta:
        model = 'orchestra.CommunicationPreference'


class StaffBotRequestFactory(factory.django.DjangoModelFactory):

    task = factory.SubFactory(TaskFactory)
    request_cause = StaffBotRequest.RequestCause.USER.value
    required_role_counter = 0

    class Meta:
        model = StaffBotRequest


class StaffingRequestInquiryFactory(factory.django.DjangoModelFactory):

    communication_preference = factory.SubFactory(
        CommunicationPreferenceFactory)
    request = factory.SubFactory(StaffBotRequestFactory)
    communication_method = (
        StaffingRequestInquiry.CommunicationMethod.SLACK.value)

    class Meta:
        model = StaffingRequestInquiry


class StaffingResponseFactory(factory.django.DjangoModelFactory):

    request_inquiry = factory.SubFactory(StaffingRequestInquiryFactory)
    is_available = False

    class Meta:
        model = StaffingResponse


@override_settings(ORCHESTRA_SLACK_EXPERTS_ENABLED=True)
def setup_models(test_case):
    """ Set up models that we'll use in multiple tests """

    # Workflow generation data
    workflows = workflow_fixtures

    # Worker generation data
    workers = {
        0: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1_ap', WorkerCertification.Role.ENTRY_LEVEL),
        ],
        1: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER),
            ('certification1_ap', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1_ap', WorkerCertification.Role.REVIEWER),
        ],
        2: [],
        3: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER),
            ('certification1_ap', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1_ap', WorkerCertification.Role.REVIEWER),
        ],
        4: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1_ap', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2_ap', WorkerCertification.Role.ENTRY_LEVEL),
        ],
        5: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2', WorkerCertification.Role.REVIEWER),
            ('certification1_ap', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2_ap', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2_ap', WorkerCertification.Role.REVIEWER),
        ],
        6: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER),
            ('certification2', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2', WorkerCertification.Role.REVIEWER),
            ('certification1_ap', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1_ap', WorkerCertification.Role.REVIEWER),
            ('certification2_ap', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2_ap', WorkerCertification.Role.REVIEWER),
        ],
        7: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER),
            ('certification1_ap', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1_ap', WorkerCertification.Role.REVIEWER),
        ],
        8: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER),
            ('certification1_ap', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1_ap', WorkerCertification.Role.REVIEWER),
        ]
    }

    # Project generation data
    projects = {
        'empty_project': 'test_workflow',
        'base_test_project': 'test_workflow',
        'test_human_and_machine': 'test_workflow_2',
        'no_task_assignments': 'test_workflow',
        'reject_entry_proj': 'test_workflow',
        'reject_rev_proj': 'test_workflow',
        'aborted_project': 'test_workflow',
        'project_to_end': 'test_workflow',
        'assignment_policy': 'assignment_policy_workflow',
        'project_management_project': 'test_workflow',
        'staffbot_assignment_policy': 'staffbot_assignment_policy_workflow',
    }

    # Task generation data
    test_case.test_version_slug = 'test_workflow'
    test_case.test_step_slug = 'step1'
    test_data = {'test_key': 'test_value'}
    tasks = {
        'review_task': {
            'project_name': 'base_test_project',
            'status': Task.Status.PENDING_REVIEW,
            'assignments': [
                (0, test_data, TaskAssignment.Status.SUBMITTED)
            ],
        },
        'awaiting_processing': {
            'project_name': 'no_task_assignments',
            'status': Task.Status.AWAITING_PROCESSING,
            'assignments': []
        },
        'rejected_entry': {
            'project_name': 'reject_entry_proj',
            'status': Task.Status.POST_REVIEW_PROCESSING,
            'assignments': [
                (4, test_data, TaskAssignment.Status.PROCESSING),
                (6, {}, TaskAssignment.Status.SUBMITTED)
            ]
        },
        'rejected_review': {
            'project_name': 'reject_rev_proj',
            'status': Task.Status.POST_REVIEW_PROCESSING,
            'assignments': [
                (5, {}, TaskAssignment.Status.SUBMITTED),
                (6, test_data, TaskAssignment.Status.PROCESSING),
                (7, {}, TaskAssignment.Status.SUBMITTED)
            ]
        },
        'project_management_task': {
            'project_name': 'project_management_project',
            'status': Task.Status.POST_REVIEW_PROCESSING,
            'assignments': [
                (5, {}, TaskAssignment.Status.SUBMITTED),
                (6, test_data, TaskAssignment.Status.PROCESSING),
                (7, {}, TaskAssignment.Status.SUBMITTED)
            ]
        },
        'aborted': {
            'project_name': 'aborted_project',
            'status': Task.Status.ABORTED,
            'assignments': [
                (4, test_data, TaskAssignment.Status.PROCESSING)
            ]
        },
    }

    # Create the objects
    _setup_workflows(test_case, workflows)
    _setup_workers(test_case, workers)
    _setup_projects(test_case, projects)
    _setup_tasks(test_case, tasks)


def _setup_workflows(test_case, workflows):
    # Create workflows
    test_case.workflows = {}
    test_case.certifications = {}
    test_case.workflow_versions = {}
    test_case.workflow_steps = {}
    for workflow_idx, workflow_details in enumerate(workflows):
        workflow = WorkflowFactory(
            slug=workflow_details['slug'],
            name=workflow_details['name'],
            code_directory='/test/dir/{}'.format(workflow_idx),
        )
        test_case.workflows[workflow_details['slug']] = workflow

        # Create certifications and dependencies
        # TODO(joshblum): workflow_step slugs may not be unique across
        # workflows! we shouldn't depend on this here
        for cert_details in workflow_details.get('certifications', []):
            certification = CertificationFactory(
                slug=cert_details['slug'],
                name=cert_details['name'],
                workflow=workflow,
            )
            test_case.certifications[cert_details['slug']] = certification

            for required_slug in cert_details['required_certifications']:
                certification.required_certifications.add(
                    test_case.certifications[required_slug])

        # Create workflow versions
        for version_details in workflow_details['versions']:
            version = WorkflowVersionFactory(
                workflow=workflow,
                slug=version_details['slug'],
                name=version_details['name'],
                description=version_details['description'],
            )
            test_case.workflow_versions[version_details['slug']] = version

            # Create workflow steps
            # TODO(joshblum): workflow_step slugs may not be unique across
            # workflows! we shouldn't depend on this here
            test_case.workflow_steps[version.slug] = {}
            workflow_steps = test_case.workflow_steps[version.slug]
            workflow_step_backrefs = []
            for step_details in version_details['steps']:
                is_human = step_details['is_human']
                step = StepFactory(
                    workflow_version=version,
                    slug=step_details['slug'],
                    name=step_details['name'],
                    is_human=is_human,
                    description=step_details.get('description', ''),

                    # TODO(dhaas): make default policies work
                    review_policy=step_details.get(
                        'review_policy',
                        get_default_review_policy(is_human)
                    ),
                    assignment_policy=step_details.get(
                        'assignment_policy',
                        get_default_assignment_policy(is_human)
                    ),
                    user_interface=step_details.get('user_interface', {}),
                    execution_function=step_details.get('execution_function',
                                                        {}),
                )
                workflow_steps[step.slug] = step

                # Add required certifications
                for required_slug in step_details.get(
                        'required_certifications', []):
                    step.required_certifications.add(
                        test_case.certifications[required_slug])

                # Add step dependencies
                workflow_step_backrefs.extend(
                    _add_step_dependencies(
                        step_details, workflow_steps, 'creation_depends_on'))
                workflow_step_backrefs.extend(
                    _add_step_dependencies(
                        step_details, workflow_steps, 'submission_depends_on'))

            # Create backreferences we missed
            _create_backrefs(test_case.workflow_steps[version.slug],
                             workflow_step_backrefs)


def _add_step_dependencies(step_dict, existing_workflow_steps, attr):
    backrefs = []
    step = existing_workflow_steps.get(step_dict['slug'])
    for dependent_slug in step_dict.get(attr, []):
        dependent_step = existing_workflow_steps.get(dependent_slug)

        # Some workflow fixtures have intentional step cycles, so
        # we create the backward references later.
        if not dependent_step:
            backrefs.append({
                'attr': attr,
                'step': step,
                'ref': dependent_slug,
            })
            continue

        getattr(step, attr).add(dependent_step)
    return backrefs


def _create_backrefs(workflow_steps, backrefs):
    for backref in backrefs:
        dependency = workflow_steps[backref['ref']]
        getattr(backref['step'], backref['attr']).add(dependency)


def _setup_workers(test_case, workers):
    # Create and certify workers
    test_case.workers = {}
    test_case.clients = {}
    test_case.comm_prefs = {}
    for user_id, certifications in workers.items():
        # Create user, worker, client
        user = (UserFactory(username='test_user_{}'.format(user_id),
                            first_name='test_first_{}'.format(user_id),
                            last_name='test_last_{}'.format(user_id),
                            email='test_user_{}@test.com'.format(user_id)))
        worker = WorkerFactory(user=user,
                               slack_user_id='test_user_{}'.format(user_id))
        test_case.workers[user_id] = worker
        test_case.comm_prefs[
            user_id] = (CommunicationPreference.objects.
                        get_or_create_all_types(worker))
        test_case.clients[user_id] = Client()
        test_case.clients[user_id].login(
            username='test_user_{}'.format(user_id),
            password='defaultpassword')

        # Assign certifications
        for slug, role in certifications:
            WorkerCertificationFactory(
                certification=test_case.certifications[slug],
                worker=test_case.workers[user_id],
                role=role)


def _setup_projects(test_case, projects):
    # Create projects
    test_case.projects = {}
    for name, workflow_slug in projects.items():
        test_case.projects[name] = ProjectFactory(
            start_datetime=BASE_DATETIME,
            workflow_version=test_case.workflow_versions[workflow_slug])
        create_project_slack_group(test_case.projects[name])


def _setup_tasks(test_case, tasks):
    # Create and assign tasks
    test_case.tasks = {}
    test_case.test_step = test_case.workflow_steps[
        test_case.test_version_slug][test_case.test_step_slug]
    for task_slug, details in tasks.items():
        task_pickup_time = BASE_DATETIME + timedelta(hours=1)
        task = TaskFactory(
            project=test_case.projects[details['project_name']],
            step=test_case.test_step,
            status=details['status'],
            start_datetime=task_pickup_time,
        )
        test_case.tasks[task_slug] = task
        for i, (user_id,
                task_data,
                assignment_status) in enumerate(details['assignments']):
            assignment = TaskAssignmentFactory(
                worker=test_case.workers[user_id],
                task=task,
                status=assignment_status,
                assignment_counter=i,
                in_progress_task_data=task_data,
                start_datetime=_new_assignment_start_datetime(task))

            # Each assignment must have at least one corresponding iteration
            Iteration.objects.create(
                assignment=assignment,
                start_datetime=assignment.start_datetime,
                end_datetime=assignment.start_datetime + ITERATION_DURATION,
                submitted_data=assignment.in_progress_task_data,
                status=Iteration.Status.REQUESTED_REVIEW)

            # Create time entry for each task.
            TimeEntryFactory(date='2016-04-04',
                             time_worked=timedelta(minutes=30),
                             assignment=assignment,
                             worker=test_case.workers[user_id],
                             description=(
                                 'test description {}'.format(assignment.id)))

        cur_assignment = current_assignment(task)
        assignments = assignment_history(task).all()
        if cur_assignment and (
                cur_assignment.status == TaskAssignment.Status.PROCESSING):
            # If there's a currently processing assignment, we'll need to
            # adjust the task's iteration sequence
            processing_counter = cur_assignment.assignment_counter
            if processing_counter != len(assignments) - 1:
                # If processing assignment is not the last in the hierarchy, we
                # need to reconstruct an iteration sequence: REQUESTED_REVIEW
                # up to the highest assignment counter, then PROVIDED_REVIEW
                # back down to the current assignment
                last_iteration = assignments.last().iterations.first()
                last_iteration.status = Iteration.Status.PROVIDED_REVIEW
                last_iteration.save()

                adjust_assignments = list(assignments)[processing_counter:-1]
                for assignment in reversed(adjust_assignments):
                    last_iteration = get_iteration_history(task).last()
                    Iteration.objects.create(
                        assignment=assignment,
                        start_datetime=last_iteration.end_datetime,
                        end_datetime=(
                            last_iteration.end_datetime + ITERATION_DURATION),
                        submitted_data=assignment.in_progress_task_data,
                        status=Iteration.Status.PROVIDED_REVIEW)

            # If there is a currently processing assignment, the task's last
            # iteration should still be processing
            last_iteration = get_iteration_history(task).last()
            last_iteration.end_datetime = None
            last_iteration.submitted_data = {}
            last_iteration.status = Iteration.Status.PROCESSING
            last_iteration.save()

        verify_iterations(task.id)


def _new_assignment_start_datetime(task):
    # Each assignment is created after the previous assignment's first
    # iteration is complete and a pickup delay elapses
    previous_assignment_duration = (
        task.assignments.count() * (ITERATION_DURATION + PICKUP_DELAY))
    return task.start_datetime + previous_assignment_duration + PICKUP_DELAY


def setup_complete_task(test_case):
    # Microseconds are truncated when manually saving models
    test_start = timezone.now().replace(microsecond=0)
    times = {
        'awaiting_pickup': test_start,
        'entry_pickup': test_start + timedelta(hours=1),
        'entry_submit': test_start + timedelta(hours=2),
        'reviewer_pickup': test_start + timedelta(hours=3),
        'reviewer_reject': test_start + timedelta(hours=4),
        'entry_resubmit': test_start + timedelta(hours=5),
        'reviewer_accept': test_start + timedelta(hours=6),
    }

    task = TaskFactory(
        project=test_case.projects['empty_project'],
        status=Task.Status.AWAITING_PROCESSING,
        step=test_case.test_step,
        start_datetime=times['awaiting_pickup'])

    workers = {
        'entry': test_case.workers[0],
        'reviewer': test_case.workers[1]
    }

    assign_task(workers['entry'].id, task.id)

    task.refresh_from_db()
    test_case.assertEquals(task.status, Task.Status.PROCESSING)

    submit_task(
        task.id, {'test': 'entry_submit'},
        Iteration.Status.REQUESTED_REVIEW,
        workers['entry'])

    task.refresh_from_db()
    test_case.assertEquals(task.status, Task.Status.PENDING_REVIEW)

    assign_task(workers['reviewer'].id, task.id)
    reviewer_assignment = task.assignments.get(
        worker=workers['reviewer'])

    # Modify assignment with correct datetime
    reviewer_assignment.start_datetime = times['reviewer_pickup']
    reviewer_assignment.save()

    task.refresh_from_db()
    test_case.assertEquals(task.status, Task.Status.REVIEWING)

    submit_task(
        task.id, {'test': 'reviewer_reject'},
        Iteration.Status.PROVIDED_REVIEW,
        workers['reviewer'])

    task.refresh_from_db()
    test_case.assertEquals(task.status, Task.Status.POST_REVIEW_PROCESSING)

    submit_task(
        task.id, {'test': 'entry_resubmit'},
        Iteration.Status.REQUESTED_REVIEW,
        workers['entry'])

    task.refresh_from_db()
    test_case.assertEquals(task.status, Task.Status.REVIEWING)

    with patch('orchestra.utils.task_lifecycle._is_review_needed',
               return_value=False):
        submit_task(
            task.id, {'test': 'reviewer_accept'},
            Iteration.Status.REQUESTED_REVIEW,
            workers['reviewer'])

    task.refresh_from_db()
    test_case.assertEquals(task.status, Task.Status.COMPLETE)
    test_case.assertEquals(task.assignments.count(), 2)
    for assignment in task.assignments.all():
        test_case.assertEquals(
            assignment.status, TaskAssignment.Status.SUBMITTED)
        test_case.assertEquals(assignment.iterations.count(), 2)

    # Modify assignments with correct datetime
    new_datetime_labels = ('entry_pickup', 'reviewer_pickup')
    for i, assignment in enumerate(assignment_history(task).all()):
        assignment.start_datetime = times[new_datetime_labels[i]]
        assignment.save()

    # Modify iterations with correct datetime
    new_datetime_labels = (
        ('entry_pickup', 'entry_submit'),
        ('reviewer_pickup', 'reviewer_reject'),
        ('reviewer_reject', 'entry_resubmit'),
        ('entry_resubmit', 'reviewer_accept')
    )
    new_datetimes = [
        (times[start_label], times[end_label])
        for start_label, end_label in new_datetime_labels]

    for i, iteration in enumerate(get_iteration_history(task)):
        iteration.start_datetime, iteration.end_datetime = new_datetimes[i]
        iteration.save()

    verify_iterations(task.id)

    return task
