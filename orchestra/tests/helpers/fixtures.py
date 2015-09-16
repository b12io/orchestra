import factory

from django.contrib.auth.models import User
from django.test import Client
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import WorkerCertification
from orchestra.slack import create_project_slack_group


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
        test_case.projects[name] = ProjectFactory(workflow_slug=workflow_slug)
        create_project_slack_group(test_case.projects[name])

    # Create and assign taks
    test_case.tasks = {}
    for task_slug, details in tasks.items():
        task = TaskFactory(project=test_case.projects[details['project_name']],
                           step_slug=test_case.test_step_slug,
                           status=details['status'])
        test_case.tasks[task_slug] = task
        for i, (user_id,
                task_data,
                assignment_status) in enumerate(details['assignments']):
            TaskAssignmentFactory(
                worker=test_case.workers[user_id],
                task=task,
                status=assignment_status,
                assignment_counter=i,
                in_progress_task_data=task_data)
