import json
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
from orchestra.models import WorkerCertification
from orchestra.project_api.api import get_workflow_steps
from orchestra.project_api.api import MalformedDependencyException
from orchestra.project_api.auth import OrchestraProjectAPIAuthentication
from orchestra.project_api.auth import SignedUser
from orchestra.utils.assignment_snapshots import empty_snapshots
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.google_apps import mock_create_drive_service


class ProjectAPITestCase(OrchestraTestCase):

    def setUp(self):  # noqa
        super(ProjectAPITestCase, self).setUp()
        setup_models(self)
        self.api_client = APIClient(enforce_csrf_checks=True)
        self.api_client.force_authenticate(user=SignedUser())

    def test_project_details_url(self):
        project = Project.objects.all()[0]
        response = self.api_client.post(
            reverse('orchestra:orchestra:project_details_url'),
            {'project_id': project.id},
            format='json')
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))
        project_details_url = returned.get('project_details_url')
        self.assertEquals(project_details_url,
                          ('http://testserver/orchestra/project_details/%s' %
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
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))

        unimportant_keys = (
            'id',
            'task',
            'short_description',
            'start_datetime',
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

        expected = {
            'project': {
                'task_class': 1,
                'workflow_slug': 'test_workflow',
                'project_data': {},
                'review_document_url': None,
                'priority': 0,
            },
            'tasks': {
                'step1': {
                    'assignments': [{
                        'snapshots': empty_snapshots(),
                        'status': 'Submitted',
                        'in_progress_task_data': {'test_key': 'test_value'},
                        'worker': 'test_user_0',
                    }],
                    'latest_data': {
                        'test_key': 'test_value'
                    },
                    'status': 'Pending Review',
                    'step_slug': 'step1',
                }
            },
            'steps': [
                ['step1', 'The longer description of the first step'],
                ['step2', 'The longer description of the second step'],
                ['step3', 'The longer description of the third step']
            ]
        }

        self.assertEquals(returned, expected)

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
        returned = json.loads(response.content.decode('utf-8'))
        del returned['tasks']['step1']['id']
        del returned['tasks']['step1']['project']
        self.assertEquals(response.status_code, 200)
        self.assertEquals(returned['tasks'], {
            'step1': {
                'assignments': [],
                'latest_data': None,
                'status': 'Awaiting Processing',
                'step_slug': 'step1'
            }
        })

    @override_settings(
        ORCHESTRA_PATHS=(('orchestra.tests.helpers.workflow', 'workflow3'),
                         ('orchestra.tests.helpers.workflow', 'workflow4'),
                         ('orchestra.tests.helpers.workflow', 'workflow5'),))
    def test_get_workflow_steps(self):
        # See orchestra.tests.helpers.workflow for workflow description
        steps = get_workflow_steps('crazy_workflow')
        slugs = [step[0] for step in steps]

        self.assertTrue(slugs.index('stepC') > slugs.index('stepA'))
        self.assertTrue(slugs.index('stepC') > slugs.index('stepB'))
        self.assertTrue(slugs.index('stepD') > slugs.index('stepA'))
        self.assertTrue(slugs.index('stepD') > slugs.index('stepB'))
        self.assertTrue(slugs.index('stepE') > slugs.index('stepC'))
        self.assertTrue(slugs.index('stepE') > slugs.index('stepD'))
        self.assertTrue(slugs.index('stepF') > slugs.index('stepE'))
        self.assertTrue(slugs.index('stepG') > slugs.index('stepF'))
        self.assertTrue(slugs.index('stepH') > slugs.index('stepF'))

        steps = get_workflow_steps('erroneous_workflow_1')

        with self.assertRaises(MalformedDependencyException):
            steps = get_workflow_steps('erroneous_workflow_2')

    @patch.object(Service, '_create_drive_service',
                  new=mock_create_drive_service)
    def test_create_project(self):
        tasks_awaiting_processing = (
            Task.objects
            .filter(status=Task.Status.AWAITING_PROCESSING)
            .count())
        response = self.api_client.post(
            '/orchestra/api/project/create_project/',
            {'workflow_slug': 'test_workflow',
             'description': 'short test description',
             'priority': 10,
             'task_class': 'real',
             'project_data': {},
             'review_document_url': 'http://test.test'},
            format='json')
        self.assertEquals(response.status_code, 200)

        self.assertEquals((Task.objects
                           .filter(status=Task.Status.AWAITING_PROCESSING)
                           .count()),
                          tasks_awaiting_processing + 1)

        # Creating a 'training' project should set task_class correctly.
        response = self.api_client.post(
            '/orchestra/api/project/create_project/',
            {'workflow_slug': 'test_workflow',
             'description': 'short test description',
             'priority': 10,
             'task_class': 'training',
             'project_data': {},
             'review_document_url': 'http://test.test'},
            format='json')
        self.assertEquals(response.status_code, 200)
        project_id = json.loads(response.content.decode('utf-8'))['project_id']
        self.assertEquals(Project.objects.get(id=project_id).task_class,
                          WorkerCertification.TaskClass.TRAINING)

        # Creating a project with missing parameters should fail.
        response = self.api_client.post(
            '/orchestra/api/project/create_project/',
            {'workflow_slug': 'test_workflow'},
            format='json')
        self.ensure_response(response,
                             {'error': 400,
                              'message': 'One of the parameters is missing'},
                             400)

    def test_workflow_types(self):
        response = self.api_client.get(
            '/orchestra/api/project/workflow_types/', format='json')
        self.assertEquals(response.status_code, 200)

        workflows = json.loads(response.content.decode('utf-8'))['workflows']
        workflows = dict(workflows)
        self.assertEquals(workflows,
                          {'test_workflow_2': 'The workflow 2',
                           'test_workflow': 'The workflow',
                           'assignment_policy_workflow': 'The workflow'})

    def test_permissions(self):
        self.api_client.force_authenticate(user=AnonymousUser())

        response = self.api_client.post(
            '/orchestra/api/project/project_information/',
            {'project_id': 1},
            format='json')
        self.assertEquals(response.status_code, 403)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(
            returned,
            {'detail': 'You do not have permission to perform this action.'})


@override_settings(ORCHESTRA_PROJECT_API_CREDENTIALS={'a': 'b'})
class ProjectAPIAuthTestCase(OrchestraTestCase):

    def setUp(self):  # noqa
        super(ProjectAPIAuthTestCase, self).setUp()
        setup_models(self)
        self.authentication = OrchestraProjectAPIAuthentication()

    def test_auth_success(self):
        self.assertEquals(
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
        self.assertEquals(
            self.authentication.fetch_user_data('a'),
            (SignedUser(), 'b'))
