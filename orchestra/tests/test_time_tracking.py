import datetime

from unittest.mock import patch

from django.utils import timezone
from rest_framework import serializers

from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import TimerError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TaskTimer
from orchestra.models import TimeEntry
from orchestra.models import Worker
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.time_tracking import _get_timer_object
from orchestra.utils.time_tracking import get_timer_current_duration
from orchestra.utils.time_tracking import save_time_entry
from orchestra.utils.time_tracking import start_timer
from orchestra.utils.time_tracking import stop_timer
from orchestra.utils.time_tracking import time_entries_for_worker


class TimeTrackingTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.worker = Worker.objects.get(user__username='test_user_6')
        self.tasks = Task.objects.filter(assignments__worker=self.worker)
        self.task = self.tasks[0]
        self.assignment = (self.task.assignments.filter(worker=self.worker)
                           .first())
        self.time_entry_data = {'date': '2016-05-01',
                                'time_worked': '00:30:00',
                                'description': 'test description'}
        self.time = timezone.now()

        def fake_now():
            """ Patch timezone.now so we can test timer. """
            return self.time

        patcher = patch('orchestra.utils.time_tracking.timezone.now', fake_now)
        self.addCleanup(patcher.stop)
        patcher.start()

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
        self.task.status = Task.Status.COMPLETE
        self.task.save()
        with self.assertRaisesRegex(TaskStatusError, 'Task already completed'):
            save_time_entry(self.worker, self.task.id, self.time_entry_data)

    def test_save_time_entry_data_invalid(self):
        # Make time entry data invalid.
        self.time_entry_data['date'] = 'aa'
        with self.assertRaises(serializers.ValidationError):
            save_time_entry(self.worker, self.tasks[0].id,
                            self.time_entry_data)

    def test_get_timer_object_created(self):
        with self.assertRaises(TaskTimer.DoesNotExist):
            self.assignment.timer
        timer = _get_timer_object(self.worker, self.task.id)
        # Timer object is attached to TaskAssignment.
        self.assignment = (self.task.assignments.filter(worker=self.worker)
                           .first())
        self.assertEqual(timer, self.assignment.timer)

    def test_get_timer_object_not_created(self):
        timer = TaskTimer(worker=self.worker, assignment=self.assignment)
        timer.save()
        new_timer = _get_timer_object(self.worker, self.task.id)

        # Function should return the already created timer object.
        self.assertEqual(new_timer, timer)

    def test_get_time_object_task_completed(self):
        self.task.status = Task.Status.COMPLETE
        self.task.save()
        timer = TaskTimer(worker=self.worker, assignment=self.assignment)
        timer.save()
        with self.assertRaisesRegex(TaskStatusError, 'Task already completed'):
            _get_timer_object(self.worker, self.task.id)

    def test_get_time_object_missing_task(self):
        with self.assertRaises(Task.DoesNotExist):
            _get_timer_object(self.worker, '111')

    def test_get_time_object_worker_not_assigned(self):
        # Find task that worker is not assigned to.
        task = Task.objects.all().exclude(id__in=[t.id for t in self.tasks])[0]
        with self.assertRaises(TaskAssignment.DoesNotExist):
            _get_timer_object(self.worker, task.id)

    def test_start_timer(self):
        start_timer(self.worker, self.task.id)
        timer = self.assignment.timer
        self.assertEqual(timer.start_time, self.time)

    def test_start_timer_already_running(self):
        timer = TaskTimer(worker=self.worker,
                          assignment=self.assignment,
                          start_time=self.time)
        timer.save()
        with self.assertRaisesRegex(TimerError, 'Timer has already started'):
            start_timer(self.worker, self.task.id)

    def test_stop_timer(self):
        timer = TaskTimer(worker=self.worker,
                          assignment=self.assignment,
                          start_time=self.time)
        timer.save()
        start_time = self.time
        self.time = self.time + datetime.timedelta(hours=1)
        time_entry = stop_timer(self.worker, self.task.id)

        # Time entry object is created correctly.
        self.assertEqual(time_entry.date, start_time.date())
        self.assertEqual(time_entry.timer_start_time, start_time)
        self.assertEqual(time_entry.time_worked, datetime.timedelta(hours=1))

        # Timer object should be reset.
        timer.refresh_from_db()
        self.assertIsNone(timer.start_time)
        self.assertIsNone(timer.stop_time)

    def test_stop_timer_not_running(self):
        timer = TaskTimer(worker=self.worker,
                          assignment=self.assignment)
        timer.save()
        with self.assertRaisesRegex(TimerError, 'Timer not started'):
            stop_timer(self.worker, self.task.id)

    def test_get_timer_current_duration(self):
        timer = TaskTimer(worker=self.worker,
                          assignment=self.assignment,
                          start_time=self.time)
        timer.save()
        self.time = self.time + datetime.timedelta(hours=1)
        duration = get_timer_current_duration(self.worker, self.task.id)
        self.assertEqual(duration, datetime.timedelta(hours=1))

    def test_get_timer_current_duration_no_start_time(self):
        timer = TaskTimer(worker=self.worker,
                          assignment=self.assignment)
        timer.save()
        duration = get_timer_current_duration(self.worker, self.task.id)
        self.assertIsNone(duration)
