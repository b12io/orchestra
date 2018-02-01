import datetime
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.core.urlresolvers import reverse
from django.test import override_settings
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.test import APIClient

from orchestra.google_apps.service import Service
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TimeEntry
from orchestra.models import WorkerCertification
from orchestra.project_api.api import MalformedDependencyException
from orchestra.project_api.api import get_workflow_steps
from orchestra.project_api.auth import OrchestraProjectAPIAuthentication
from orchestra.project_api.auth import SignedUser
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.google_apps import mock_create_drive_service
from orchestra.utils.load_json import load_encoded_json
from orchestra.utils.task_lifecycle import get_new_task_assignment


class ProjectAPITestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.api_client = APIClient(enforce_csrf_checks=True)
        self.api_client.force_authenticate(user=SignedUser())

    def test_project_details_url(self):
        project = Project.objects.all()[0]
        response = self.api_client.post(
            reverse('orchestra:orchestra:project_details_url'),
            {'project_id': project.id},
            format='json')
        self.assertEqual(response.status_code, 200)
        returned = load_encoded_json(response.content)
        project_details_url = returned.get('project_details_url')
        self.assertEqual(project_details_url,
                         ('http://testserver/orchestra/app/project/%s' %
                          project.id))

        response = self.api_client.post(
            '/orchestra/api/project/project_details_url/',
            {},
            format='json')

        self.ensure_response(response,
                             {'error': 400,
                              'message': 'project_id parameter is missing'},
                             400)

    def test_project_information(self):
        project = self.projects['base_test_project']
        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_id': project.id},
            format='json')
        self.assertEqual(response.status_code, 200)
        returned = load_encoded_json(response.content)

        unimportant_keys = (
            'id',
            'task',
            'short_description',
            'start_datetime',
            'end_datetime'
        )

        def delete_keys(obj):
            if isinstance(obj, list):
                for item in obj:
                    delete_keys(item)

            elif isinstance(obj, dict):
                for key in unimportant_keys:
                    try:
                        del obj[key]
                    except KeyError:
                        pass
                for value in obj.values():
                    delete_keys(value)

        delete_keys(returned)
        del returned['tasks']['step1']['project']
        del (returned['tasks']['step1']['assignments'][0]
                     ['iterations'][0]['assignment'])

        expected = {
            'project': {
                'task_class': 1,
                'workflow_slug': 'w1',
                'workflow_version_slug': 'test_workflow',
                'project_data': {},
                'team_messages_url': None,
                'priority': 0,
            },
            'tasks': {
                'step1': {
                    'assignments': [{
                        'status': 'Submitted',
                        'in_progress_task_data': {'test_key': 'test_value'},
                        'worker': {
                            'username': self.workers[0].user.username,
                            'first_name': self.workers[0].user.first_name,
                            'last_name': self.workers[0].user.last_name,
                            'slack_username':
                                self.workers[0].slack_username,
                            'slack_user_id':
                                self.workers[0].slack_user_id
                        },
                        'iterations': [{
                            'status': 'Requested Review',
                            'submitted_data': {'test_key': 'test_value'},
                        }],
                        'recorded_work_time': 30*60,
                    }],
                    'latest_data': {
                        'test_key': 'test_value'
                    },
                    'status': 'Pending Review',
                    'step_slug': 'step1',
                }
            },
            'steps': [
                {'slug': 'step1',
                 'description': 'The longer description of the first step',
                 'is_human': True,
                 'name': 'The first step'},
                {'slug': 'step2',
                 'description': 'The longer description of the second step',
                 'is_human': True,
                 'name': 'The second step'},
                {'slug': 'step3',
                 'description': 'The longer description of the third step',
                 'is_human': True,
                 'name': 'The third step'}
            ]
        }

        self.assertEqual(returned, expected)

        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_id': -1},
            format='json')
        self.ensure_response(response,
                             {'error': 400,
                              'message': 'No project for given id'},
                             400)

        # Getting project info without a project_id should fail.
        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'projetc_id': project.id},  # Typo.
            format='json')
        self.ensure_response(response,
                             {'error': 400,
                              'message': 'project_id is required'},
                             400)

        # Retrieve the third project, which has no task assignments.
        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_id': self.projects['no_task_assignments'].id},
            format='json')
        returned = load_encoded_json(response.content)
        for key in ('id', 'project', 'start_datetime'):
            del returned['tasks']['step1'][key]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(returned['tasks'], {
            'step1': {
                'assignments': [],
                'latest_data': None,
                'status': 'Awaiting Processing',
                'step_slug': 'step1'
            }
        })

    def test_project_assignment_recorded_time(self):
        project = self.projects['base_test_project']
        worker = self.workers[0]

        task = self.tasks['review_task']
        assignment = TaskAssignment.objects.filter(
            worker=worker, task=task).first()
        other_assignment = get_new_task_assignment(
            worker, Task.Status.AWAITING_PROCESSING)

        # create 3 time entries
        TimeEntry.objects.create(
            worker=self.workers[0],
            date=datetime.datetime.now().date(),
            time_worked=datetime.timedelta(hours=1),
            assignment=assignment)
        TimeEntry.objects.create(
            worker=self.workers[0],
            date=datetime.datetime.now().date(),
            time_worked=datetime.timedelta(hours=1),
            assignment=other_assignment)
        TimeEntry.objects.create(
            worker=self.workers[0],
            date=datetime.datetime.now().date(),
            time_worked=datetime.timedelta(minutes=15),
            assignment=assignment)

        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_id': project.id},
            format='json')
        returned = load_encoded_json(response.content)
        returned_task = returned['tasks']
        returned_assignment = returned_task['step1']['assignments'][0]
        recorded_time = returned_assignment['recorded_work_time']
        self.assertEqual(recorded_time, 105*60)  # 1:15 + 0:30

    def test_get_workflow_steps(self):
        # See orchestra.tests.helpers.fixtures for workflow description
        steps = get_workflow_steps('w3', 'crazy_workflow')
        slugs = [step['slug'] for step in steps]

        self.assertTrue(slugs.index('stepC') > slugs.index('stepA'))
        self.assertTrue(slugs.index('stepC') > slugs.index('stepB'))
        self.assertTrue(slugs.index('stepD') > slugs.index('stepA'))
        self.assertTrue(slugs.index('stepD') > slugs.index('stepB'))
        self.assertTrue(slugs.index('stepE') > slugs.index('stepC'))
        self.assertTrue(slugs.index('stepE') > slugs.index('stepD'))
        self.assertTrue(slugs.index('stepF') > slugs.index('stepE'))
        self.assertTrue(slugs.index('stepG') > slugs.index('stepF'))
        self.assertTrue(slugs.index('stepH') > slugs.index('stepF'))

        steps = get_workflow_steps('w4', 'erroneous_workflow_1')

        with self.assertRaises(MalformedDependencyException):
            steps = get_workflow_steps('w5', 'erroneous_workflow_2')

    @patch.object(Service, '_create_drive_service',
                  new=mock_create_drive_service)
    def test_create_project(self):
        tasks_awaiting_processing = (
            Task.objects
            .filter(status=Task.Status.AWAITING_PROCESSING)
            .count())
        response = self.api_client.post(
            '/orchestra/api/project/create_project/',
            {'workflow_slug': 'w1',
             'workflow_version_slug': 'test_workflow',
             'description': 'short test description',
             'priority': 10,
             'task_class': 'real',
             'project_data': {}},
            format='json')
        self.assertEqual(response.status_code, 200)

        self.assertEqual((Task.objects
                          .filter(status=Task.Status.AWAITING_PROCESSING)
                          .count()),
                         tasks_awaiting_processing + 1)

        # Creating a 'training' project should set task_class correctly.
        response = self.api_client.post(
            '/orchestra/api/project/create_project/',
            {'workflow_slug': 'w1',
             'workflow_version_slug': 'test_workflow',
             'description': 'short test description',
             'priority': 10,
             'task_class': 'training',
             'project_data': {}},
            format='json')
        self.assertEqual(response.status_code, 200)
        project_id = load_encoded_json(response.content)['project_id']
        self.assertEqual(Project.objects.get(id=project_id).task_class,
                         WorkerCertification.TaskClass.TRAINING)

        # Creating a project with missing parameters should fail.
        response = self.api_client.post(
            '/orchestra/api/project/create_project/',
            {'workflow_slug': 'w1'},
            format='json')
        self.ensure_response(response,
                             {'error': 400,
                              'message': 'One of the parameters is missing'},
                             400)

    def test_workflow_types(self):
        response = self.api_client.get(
            '/orchestra/api/project/workflow_types/', format='json')
        self.assertEqual(response.status_code, 200)

        workflows = load_encoded_json(response.content)['workflows']
        workflows = dict(workflows)
        self.assertEqual(
            workflows,
            {
                workflow_slug: {
                    'name': workflow.name,
                    'versions': {
                        v.slug: {
                            'name': v.name,
                            'description': v.description,
                        }
                        for v in workflow.versions.all()
                    }
                }
                for workflow_slug, workflow in self.workflows.items()
            }
        )

    def _make_assign_worker_task_request(self, worker_id,
                                         task_id, success=True):
        response = self.api_client.post(
            '/orchestra/api/project/assign_worker_to_task/',
            {
                'worker_id': worker_id,
                'task_id': task_id,
            },
            format='json')
        self.assertEqual(response.status_code, 200)
        data = load_encoded_json(response.content)
        self.assertEqual(data['success'], success)
        return data

    def test_assign_worker_to_task(self):
        worker = self.workers[0]

        # We should be able to assign to an unassigned task
        task = self.tasks['awaiting_processing']
        query = TaskAssignment.objects.filter(worker=worker, task=task)
        self.assertFalse(query.exists())
        data = self._make_assign_worker_task_request(worker.id, task.id)
        self.assertTrue(query.exists())
        query.delete()

        # Nonsense arguments
        task = self.tasks['awaiting_processing']
        query = TaskAssignment.objects.filter(worker=worker, task=task)
        self.assertFalse(query.exists())
        data = self._make_assign_worker_task_request(None, None, success=False)
        self.assertTrue('error' in data['errors'])
        self.assertFalse(query.exists())

        # Invalid Worker
        task = self.tasks['awaiting_processing']
        query = TaskAssignment.objects.filter(worker=worker, task=task)
        self.assertFalse(query.exists())
        data = self._make_assign_worker_task_request(
            -1, task.id, success=False)
        self.assertTrue('error' in data['errors'])
        self.assertFalse(query.exists())

        # Invalid Task
        task = self.tasks['awaiting_processing']
        query = TaskAssignment.objects.filter(worker=worker, task=task)
        self.assertFalse(query.exists())
        data = self._make_assign_worker_task_request(
            worker.id, -1, success=False)
        self.assertTrue('error' in data['errors'])
        self.assertFalse(query.exists())

        # Worker0 is not a reviewer so this should fail
        task = self.tasks['review_task']
        data = self._make_assign_worker_task_request(
            worker.id, task.id, success=False)
        self.assertTrue('worker_certification_error' in data['errors'])
        self.assertFalse(query.exists())

        # Can't assign to aborted task
        task = self.tasks['aborted']
        data = self._make_assign_worker_task_request(
            worker.id, task.id, success=False)
        self.assertTrue('task_assignment_error' in data['errors'])
        self.assertFalse(query.exists())

    def test_permissions(self):
        self.api_client.force_authenticate(user=AnonymousUser())

        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_id': 1},
            format='json')
        self.assertEqual(response.status_code, 403)
        returned = load_encoded_json(response.content)
        self.assertEqual(
            returned,
            {'detail': 'You do not have permission to perform this action.'})


@override_settings(ORCHESTRA_PROJECT_API_CREDENTIALS={'a': 'b'})
class ProjectAPIAuthTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.authentication = OrchestraProjectAPIAuthentication()

    def test_auth_success(self):
        self.assertEqual(
            self.authentication.fetch_user_data('a'),
            (SignedUser(), 'b'))

    def test_no_key(self):
        with self.assertRaises(AuthenticationFailed):
            self.authentication.fetch_user_data('c')

    def test_misconfigured_credentials(self):
        tmp_setting = settings.ORCHESTRA_PROJECT_API_CREDENTIALS
        del settings.ORCHESTRA_PROJECT_API_CREDENTIALS
        with self.assertRaises(AuthenticationFailed):
            self.authentication.fetch_user_data('a')
        settings.ORCHESTRA_PROJECT_API_CREDENTIALS = tmp_setting
        self.assertEqual(
            self.authentication.fetch_user_data('a'),
            (SignedUser(), 'b'))
