import factory

from copy import deepcopy
from dateutil.parser import parse
from django.contrib.auth.models import User
from django.test import Client
from django.test import override_settings
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import WorkerCertification
from orchestra.models import Workflow
from orchestra.models import Step
from orchestra.models import WorkflowVersion
from orchestra.slack import create_project_slack_group
from orchestra.utils.task_properties import assignment_history
from orchestra.tests.helpers.workflow import workflow_fixtures
from orchestra.workflow.defaults import get_default_assignment_policy
from orchestra.workflow.defaults import get_default_review_policy


class WorkflowFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Workflow


class WorkflowVersionFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = WorkflowVersion


class StepFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = Step


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


class TaskAssignmentFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = 'orchestra.TaskAssignment'

    status = TaskAssignment.Status.PROCESSING
    snapshots = {}


@override_settings(SLACK_EXPERTS=True)
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


def _setup_projects(test_case, projects):
    # Create projects
    test_case.projects = {}
    for name, workflow_slug in projects.items():
        test_case.projects[name] = ProjectFactory(
            start_datetime=parse('2015-10-12T00:00:00+00:00'),
            workflow_version=test_case.workflow_versions[workflow_slug])
        create_project_slack_group(test_case.projects[name])


def _setup_tasks(test_case, tasks):
    # Create and assign tasks
    test_case.tasks = {}
    test_case.test_step = test_case.workflow_steps[
        test_case.test_version_slug][test_case.test_step_slug]
    for task_slug, details in tasks.items():
        task = TaskFactory(
            project=test_case.projects[details['project_name']],
            step=test_case.test_step,
            status=details['status'],
            start_datetime=parse('2015-10-12T01:00:00+00:00'),
        )
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
