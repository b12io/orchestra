import datetime

from rest_framework import serializers

from orchestra.core.errors import TaskStatusError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TimeEntry
from orchestra.models import Worker
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.time_tracking import save_time_entry
from orchestra.utils.time_tracking import time_entries_for_worker


class TimeTrackingTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.tasks = Task.objects.filter(assignments__worker=self.worker)
        self.time_entry_data = {'date': '2016-05-01',
                                'time_worked': '00:30:00',
                                'description': 'test description'}

    def verify_time_entry_serialization(self, time_entry):
        self.assertEqual(time_entry['date'], '2016-04-04')
        self.assertEqual(time_entry['time_worked'], '00:30:00')
        self.assertEqual(time_entry['description'],
                         ('test description {}'
                          .format(time_entry['assignment'])))

    def test_time_entries_for_worker(self):
        # Verify that function returns all time entries for worker.
        time_entries = time_entries_for_worker(self.worker)
        self.assertEqual(len(time_entries), self.tasks.count())
        for time_entry in time_entries:
            self.verify_time_entry_serialization(time_entry)

    def test_time_entries_for_worker_and_task_id(self):
        time_entries = time_entries_for_worker(self.worker, self.tasks[0].id)
        self.assertEqual(len(time_entries), 1)
        self.verify_time_entry_serialization(time_entries[0])

    def test_time_entries_for_worker_and_task_id_task_missing(self):
        with self.assertRaises(Task.DoesNotExist):
            time_entries_for_worker(self.worker, '1111')

    def test_time_entries_for_worker_and_task_id_worker_not_assigned(self):
        # Find task that worker is not assigned to.
        task = Task.objects.all().exclude(id__in=[t.id for t in self.tasks])[0]
        with self.assertRaises(TaskAssignment.DoesNotExist):
            time_entries_for_worker(self.worker, task.id)

    def test_save_time_entry(self):
        time_entry = save_time_entry(self.worker, self.tasks[0].id,
                                     self.time_entry_data)
        self.assertEqual(
            TimeEntry.objects.filter(assignment__worker=self.worker).count(),
            self.tasks.count() + 1)
        self.assertEqual(
            TimeEntry.objects.filter(assignment__worker=self.worker,
                                     assignment__task=self.tasks[0]).count(),
            2)
        self.assertEqual(time_entry.time_worked,
                         datetime.timedelta(minutes=30))
        self.assertEqual(time_entry.description, 'test description')

    def test_save_time_entry_task_missing(self):
        with self.assertRaises(Task.DoesNotExist):
            save_time_entry(self.worker, '1111', self.time_entry_data)

    def test_save_time_entry_worker_not_assigned(self):
        # Find task that worker is not assigned to.
        task = Task.objects.all().exclude(id__in=[t.id for t in self.tasks])[0]
        with self.assertRaises(TaskAssignment.DoesNotExist):
            save_time_entry(self.worker, task.id, self.time_entry_data)

    def test_save_time_entry_task_complete(self):
        task = self.tasks[0]
        task.status = Task.Status.COMPLETE
        task.save()
        with self.assertRaisesRegex(TaskStatusError, 'Task already completed'):
            save_time_entry(self.worker, task.id, self.time_entry_data)

    def test_save_time_entry_data_invalid(self):
        # Make time entry data invalid.
        self.time_entry_data['date'] = 'aa'
        with self.assertRaises(serializers.ValidationError):
            save_time_entry(self.worker, self.tasks[0].id,
                            self.time_entry_data)
