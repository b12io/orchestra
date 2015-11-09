import factory

from copy import deepcopy
from dateutil.parser import parse
from django.contrib.auth.models import User
from django.test import Client
from django.test import override_settings
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import WorkerCertification
from orchestra.slack import create_project_slack_group
from orchestra.utils.task_properties import assignment_history


class UserFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = User

    password = factory.PostGenerationMethodCall('set_password',
                                                'defaultpassword')


class WorkerFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'orchestra.Worker'


class CertificationFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'orchestra.Certification'


class WorkerCertificationFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'orchestra.WorkerCertification'

    task_class = WorkerCertification.TaskClass.REAL


class ProjectFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'orchestra.Project'

    short_description = factory.Sequence(
        lambda n: 'Project {}'.format(n))
    priority = 0
    task_class = WorkerCertification.TaskClass.REAL


class TaskFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'orchestra.Task'

    step_slug = 'step1'


class TaskAssignmentFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'orchestra.TaskAssignment'

    status = TaskAssignment.Status.PROCESSING
    snapshots = {}


@override_settings(SLACK_EXPERTS=True)
def setup_models(test_case):
    """ Set up models that we'll use in multiple tests """
    # Certification generation data
    certifications = [
        {
            'slug': 'certification1',
            'name': 'The first certification',
            'required_certifications': []
        },
        {
            'slug': 'certification2',
            'name': 'The second certification',
            'required_certifications': ['certification1']
        }
    ]

    # Worker generation data
    workers = {
        0: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL)
        ],
        1: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER)
        ],
        2: [],
        3: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER)
        ],
        4: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2', WorkerCertification.Role.ENTRY_LEVEL)
        ],
        5: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2', WorkerCertification.Role.REVIEWER)
        ],
        6: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER),
            ('certification2', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification2', WorkerCertification.Role.REVIEWER)
        ],
        7: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER)
        ],
        8: [
            ('certification1', WorkerCertification.Role.ENTRY_LEVEL),
            ('certification1', WorkerCertification.Role.REVIEWER)
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
    }

    # Task generation data
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
        'processing_task': {
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
        'aborted': {
            'project_name': 'aborted_project',
            'status': Task.Status.ABORTED,
            'assignments': [
                (4, test_data, TaskAssignment.Status.PROCESSING)
            ]
        },
        'to_be_ended_1': {
            'project_name': 'project_to_end',
            'status': Task.Status.POST_REVIEW_PROCESSING,
            'assignments': [
                (5, {}, TaskAssignment.Status.SUBMITTED),
                (6, test_data, TaskAssignment.Status.PROCESSING),
                (7, {}, TaskAssignment.Status.SUBMITTED)
            ]
        },
        'to_be_ended_2': {
            'project_name': 'project_to_end',
            'status': Task.Status.PROCESSING,
            'assignments': [
                (4, test_data, TaskAssignment.Status.SUBMITTED)
            ]
        },
    }

    # Create certifications and dependencies
    test_case.certifications = {}
    for details in certifications:
        new_slug = details['slug']
        test_case.certifications[new_slug] = CertificationFactory(
            slug=new_slug, name=details['name'])
        for required_slug in details['required_certifications']:
            test_case.certifications[new_slug].required_certifications.add(
                test_case.certifications[required_slug])

    # Create and certify workers
    test_case.workers = {}
    test_case.clients = {}
    for user_id, certifications in workers.items():
        # Create user, worker, client
        user = (UserFactory(username='test_user_{}'.format(user_id),
                            first_name='test_first_{}'.format(user_id),
                            last_name='test_last_{}'.format(user_id),
                            password='test_{}'.format(user_id),
                            email='test_user_{}@test.com'.format(user_id)))
        test_case.workers[user_id] = WorkerFactory(user=user)
        test_case.clients[user_id] = Client()
        test_case.clients[user_id].login(
            username='test_user_{}'.format(user_id),
            password='test_{}'.format(user_id))

        # Assign certifications
        for slug, role in certifications:
            WorkerCertificationFactory(
                certification=test_case.certifications[slug],
                worker=test_case.workers[user_id],
                role=role)

    # Create projects
    test_case.projects = {}
    for name, workflow_slug in projects.items():
        test_case.projects[name] = ProjectFactory(
            workflow_slug=workflow_slug,
            start_datetime=parse('2015-10-12T00:00:00+00:00'))
        create_project_slack_group(test_case.projects[name])

    # Create and assign taks
    test_case.tasks = {}
    for task_slug, details in tasks.items():
        task = TaskFactory(project=test_case.projects[details['project_name']],
                           step_slug=test_case.test_step_slug,
                           status=details['status'],
                           start_datetime=parse('2015-10-12T01:00:00+00:00'))
        test_case.tasks[task_slug] = task
        for i, (user_id,
                task_data,
                assignment_status) in enumerate(details['assignments']):
            TaskAssignmentFactory(
                worker=test_case.workers[user_id],
                task=task,
                status=assignment_status,
                assignment_counter=i,
                in_progress_task_data=task_data,
                start_datetime=parse(
                    '2015-10-12T0{}:00:00+00:00'.format(2 + i)))


def setup_task_history(test):
    task = test.tasks['rejected_review']

    test._submit_assignment(
        test.clients[6], task.id, seconds=35)
    test._submit_assignment(
        test.clients[7], task.id, command='reject', seconds=36)
    test._submit_assignment(
        test.clients[6], task.id, seconds=37)
    test._submit_assignment(
        test.clients[7], task.id, command='accept', seconds=38)

    # Fill out the snapshots for all assignments
    assignments = assignment_history(task)
    first_assignment = assignments[0]
    second_assignment = assignments[1]
    third_assignment = assignments[2]

    first_assignment.snapshots['snapshots'] = deepcopy(
        second_assignment.snapshots['snapshots'])
    second_assignment.snapshots['snapshots'] = (
        deepcopy(third_assignment.snapshots['snapshots']) +
        second_assignment.snapshots['snapshots'])[:-1]

    def fix_datetimes(snapshots, new_datetimes):
        for snapshot, new_datetime in zip(snapshots, new_datetimes):
            snapshot['datetime'] = new_datetime

    # Explicitly set the iteration datetimes.  If we didn't, the timestamps
    # would be `datetime.now`, which we can't test against.  The explicitly set
    # times are predictable distance apart, so we can test the
    # resulting latency reports.
    fix_datetimes(
        first_assignment.snapshots['snapshots'],
        ['2015-10-12T02:02:00+00:00', '2015-10-12T03:05:00+00:00'])
    fix_datetimes(
        second_assignment.snapshots['snapshots'],
        ['2015-10-12T03:01:00+00:00', '2015-10-12T03:07:00+00:00',
         '2015-10-12T04:03:00+00:00', '2015-10-12T04:10:00+00:00'])
    fix_datetimes(
        third_assignment.snapshots['snapshots'],
        ['2015-10-12T04:02:00+00:00', '2015-10-12T04:13:00+00:00'])

    first_assignment.save()
    second_assignment.save()
    third_assignment.save()

    return task
