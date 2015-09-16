from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import end_project
from orchestra.utils.task_lifecycle import submit_task
from orchestra.utils.task_properties import is_worker_assigned_to_task


class BasicNotificationsTestCase(OrchestraTestCase):
    """
    Test modular functions in the notifications module
    """
    def setUp(self):  # noqa
        super(BasicNotificationsTestCase, self).setUp()
        setup_models(self)

    @override_settings(SLACK_INTERNAL=True)
    def test_notify_status_change(self):
        slack_messages = self.slack.get_messages(
            settings.SLACK_INTERNAL_NOTIFICATION_CHANNEL)

        def _validate_slack_messages(message_stub):
            """
            Check that correct slack message was sent if API key present.
            """
            self.assertTrue(message_stub in slack_messages.pop())

        project = self.projects['empty_project']
        task = TaskFactory(project=project,
                           step_slug=self.test_step_slug,
                           status=Task.Status.AWAITING_PROCESSING)

        # Entry-level worker picks up task
        self.assertEquals(task.status, Task.Status.AWAITING_PROCESSING)
        task = assign_task(self.workers[0].id, task.id)
        self.assertTrue(is_worker_assigned_to_task(self.workers[0], task))

        # Notification should be sent to entry-level worker
        self.assertEquals(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEquals(notification['recipient'],
                          self.workers[0].user.email)
        self.assertEquals(notification['subject'],
                          "You've been assigned to a new task!")

        _validate_slack_messages('Task has been picked up by a worker.')
        self.assertEquals(len(slack_messages), 0)

        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=True):
            # Entry-level worker submits task
            task = submit_task(task.id, {}, TaskAssignment.SnapshotType.SUBMIT,
                               self.workers[0], 0)

        self.assertEquals(task.status, Task.Status.PENDING_REVIEW)
        # Notification should be sent to entry-level worker
        self.assertEquals(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEquals(notification['recipient'],
                          self.workers[0].user.email)
        self.assertEquals(notification['subject'],
                          'Your task is under review!')

        _validate_slack_messages('Task is awaiting review.')
        self.assertEquals(len(slack_messages), 0)

        # Reviewer picks up task
        task = assign_task(self.workers[1].id, task.id)
        self.assertEquals(task.status, Task.Status.REVIEWING)
        # No notification should be sent
        self.assertEquals(len(self.mail.inbox), 0)

        _validate_slack_messages('Task is under review.')
        self.assertEquals(len(slack_messages), 0)

        # Reviewer rejects task
        task = submit_task(task.id, {}, TaskAssignment.SnapshotType.REJECT,
                           self.workers[1], 0)
        self.assertEquals(task.status, Task.Status.POST_REVIEW_PROCESSING)
        # Notification should be sent to original worker
        self.assertEquals(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEquals(notification['recipient'],
                          self.workers[0].user.email)
        self.assertEquals(notification['subject'],
                          'Your task has been returned')

        _validate_slack_messages('Task was returned by reviewer.')
        self.assertEquals(len(slack_messages), 0)

        # Entry-level worker resubmits task
        task = submit_task(task.id, {}, TaskAssignment.SnapshotType.SUBMIT,
                           self.workers[0], 0)
        self.assertEquals(task.status, Task.Status.REVIEWING)
        # Notification should be sent to reviewer
        self.assertEquals(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEquals(notification['recipient'],
                          self.workers[1].user.email)
        self.assertEquals(notification['subject'],
                          'A task is ready for re-review!')

        _validate_slack_messages('Task is under review.')
        self.assertEquals(len(slack_messages), 0)

        # First reviewer accepts task
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=True):
            task = submit_task(task.id, {}, TaskAssignment.SnapshotType.ACCEPT,
                               self.workers[1], 0)
        self.assertEquals(task.status, Task.Status.PENDING_REVIEW)
        # Notification should be sent to first reviewer
        self.assertEquals(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEquals(notification['recipient'],
                          self.workers[1].user.email)
        self.assertEquals(notification['subject'],
                          'Your task is under review!')

        _validate_slack_messages('Task is awaiting review.')
        self.assertEquals(len(slack_messages), 0)

        # Second reviewer picks up task
        task = assign_task(self.workers[3].id, task.id)
        self.assertEquals(task.status, Task.Status.REVIEWING)
        # No notification should be sent
        self.assertEquals(len(self.mail.inbox), 0)

        _validate_slack_messages('Task is under review.')
        self.assertEquals(len(slack_messages), 0)

        # Second reviewer rejects task
        task = submit_task(task.id, {}, TaskAssignment.SnapshotType.REJECT,
                           self.workers[3], 0)
        self.assertEquals(task.status, Task.Status.POST_REVIEW_PROCESSING)
        # Notification should be sent to first reviewer
        self.assertEquals(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEquals(notification['recipient'],
                          self.workers[1].user.email)
        self.assertEquals(notification['subject'],
                          'Your task has been returned')

        _validate_slack_messages('Task was returned by reviewer.')
        self.assertEquals(len(slack_messages), 0)

        # First reviewer resubmits task
        task = submit_task(task.id, {}, TaskAssignment.SnapshotType.SUBMIT,
                           self.workers[1], 0)
        self.assertEquals(task.status, Task.Status.REVIEWING)
        # Notification should be sent to second reviewer
        self.assertEquals(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEquals(notification['recipient'],
                          self.workers[3].user.email)
        self.assertEquals(notification['subject'],
                          'A task is ready for re-review!')

        _validate_slack_messages('Task is under review.')
        self.assertEquals(len(slack_messages), 0)

        # Second reviewer accepts task; task is complete
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            task = submit_task(task.id, {}, TaskAssignment.SnapshotType.ACCEPT,
                               self.workers[3], 0)
        self.assertEquals(task.status, Task.Status.COMPLETE)

        # Notification should be sent to all workers on task
        self.assertEquals(len(self.mail.inbox), 3)
        recipients = {mail['recipient'] for mail in self.mail.inbox}
        subjects = {mail['subject'] for mail in self.mail.inbox}
        self.assertEquals(recipients,
                          {self.workers[uid].user.email for uid in (0, 1, 3)})
        self.assertEquals(subjects, {'Task complete!'})
        self.mail.clear()

        _validate_slack_messages('Task has been completed.')
        self.assertEquals(len(slack_messages), 0)

        # End project
        end_project(task.project.id)
        task = Task.objects.get(id=task.id)
        self.assertEquals(task.status, Task.Status.ABORTED)

        # Notification should be sent to all workers on task
        self.assertEquals(len(self.mail.inbox), 3)
        recipients = {mail['recipient'] for mail in self.mail.inbox}
        subjects = {mail['subject'] for mail in self.mail.inbox}
        self.assertEquals(recipients,
                          {self.workers[uid].user.email for uid in (0, 1, 3)})
        self.assertEquals(subjects,
                          {'A task you were working on has been ended'})
        self.mail.clear()

        for task in project.tasks.all():
            _validate_slack_messages('Task has been aborted.')
        self.assertEquals(len(slack_messages), 0)
