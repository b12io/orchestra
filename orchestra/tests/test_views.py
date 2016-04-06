import json

from unittest.mock import patch

from django.test import RequestFactory

from orchestra.models import Task
from orchestra.models import Worker
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.views import time_entries


class TimeEntriesViewTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.factory = RequestFactory()
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.tasks = Task.objects.filter(assignments__worker=self.worker)
        self.time_entry_data = {'date': '2016-05-01',
                                'time_worked': '00:30:00',
                                'description': 'test description'}

    def create_get_request(self, params=None):
        if params:
            self.request = self.factory.get('/api/interface/time_entries/',
                                            data=params)
        else:
            self.request = self.factory.get('/api/interface/time_entries/')
        self.request.user = self.worker.user

    def create_post_request(self):
        self.post_request = self.factory.post(
            '/api/interface/time_entries/',
            data=json.dumps(self.time_entry_data),
            content_type='application/json')
        self.post_request.user = self.worker.user

    def test_time_entries_get(self):
        self.create_get_request()
        resp = time_entries(self.request)
        data = json.loads(resp.content.decode())
        self.assertEqual(len(data), self.tasks.count())

    @patch('orchestra.views.time_entries_for_worker')
    def test_time_entries_get_task_id(self, mock_func):
        mock_func.return_value = [self.time_entry_data]
        self.create_get_request(params={'task-id': self.tasks[0].id})
        time_entries(self.request)
        mock_func.assert_called_with(self.worker,
                                     task_id=str(self.tasks[0].id))

    @patch('orchestra.views.time_entries_for_worker')
    def test_time_entries_get_task_missing(self, mock_func):
        mock_func.side_effect = Task.DoesNotExist
        self.create_get_request()
        resp = time_entries(self.request)
        self.assertEqual(resp.status_code, 400)
        data = json.loads(resp.content.decode())
        self.assertEqual(data['message'], 'No task for given id')
        self.assertEqual(data['error'], 400)

    @patch('orchestra.views.time_entries_for_worker')
    def test_time_entries_get_worker_not_assigned(self, mock_func):
        pass

    @patch('orchestra.views.save_time_entry')
    def test_time_entries_post(self, mock_func):
        mock_func.return_value = self.time_entry_data

        # Set task id in request body.
        self.time_entry_data['task_id'] = self.tasks[0].id
        self.create_post_request()
        time_entries(self.post_request)

        # Remove task_id from dictionary so we can compare with mock_func
        # call.
        self.time_entry_data.pop('task_id')
        mock_func.assert_called_with(self.worker, self.tasks[0].id,
                                     self.time_entry_data)

    @patch('orchestra.views.time_entries_for_worker')
    def test_time_entries_post_task_missing(self, mock_func):
        pass

    @patch('orchestra.views.time_entries_for_worker')
    def test_time_entries_post_worker_not_assigned(self, mock_func):
        pass
