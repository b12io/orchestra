from unittest.mock import patch

from django.conf import settings
from django.test import override_settings

from orchestra.communication.slack import _project_slack_group_name
from orchestra.models import Iteration
from orchestra.models import Task
from orchestra.models import Project
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import end_project
from orchestra.utils.task_lifecycle import set_project_status
from orchestra.utils.task_lifecycle import submit_task


class BasicNotificationsTestCase(OrchestraTestCase):
    """
    Test modular functions in the notifications module
    """

    def setUp(self):
        super().setUp()
        setup_models(self)

    @override_settings(ORCHESTRA_SLACK_INTERNAL_ENABLED=True)
    @override_settings(ORCHESTRA_SLACK_EXPERTS_ENABLED=True)
    def test_notify_status_change(self):
        project = self.projects['empty_project']
        internal_name = settings.SLACK_INTERNAL_NOTIFICATION_CHANNEL.strip('#')
        internal_groups = [
            group for group in self.slack.conversations.list().body['channels']
            if group['name'] == internal_name]
        internal_group_id = internal_groups[0]['id']
        internal_slack_messages = self.slack.get_messages(internal_group_id)
        experts_slack_messages = self.slack.get_messages(
            project.slack_group_id)

        def _validate_slack_messages(message_stub):
            """
            Check that correct slack message was sent if API key present.
            """
            self.assertIn(message_stub, internal_slack_messages.pop())
            self.assertIn(message_stub, experts_slack_messages.pop())

        task = TaskFactory(project=project,
                           step=self.test_step,
                           status=Task.Status.AWAITING_PROCESSING)

        # Entry-level worker picks up task
        self.assertEqual(task.status, Task.Status.AWAITING_PROCESSING)
        task = assign_task(self.workers[0].id, task.id)
        self.assertTrue(task.is_worker_assigned(self.workers[0]))

        # Notification should be sent to entry-level worker
        self.assertEqual(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEqual(notification['recipient'],
                         self.workers[0].user.email)
        self.assertEqual(notification['subject'],
                         "You've been assigned to a new task!")

        _validate_slack_messages('Task has been picked up by a worker.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=True):
            # Entry-level worker submits task
            task = submit_task(task.id, {}, Iteration.Status.REQUESTED_REVIEW,
                               self.workers[0])

        self.assertEqual(task.status, Task.Status.PENDING_REVIEW)
        # Notification should be sent to entry-level worker
        self.assertEqual(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEqual(notification['recipient'],
                         self.workers[0].user.email)
        self.assertEqual(notification['subject'],
                         'Your task is under review!')

        _validate_slack_messages('Task is awaiting review.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        # Reviewer picks up task
        task = assign_task(self.workers[1].id, task.id)
        self.assertEqual(task.status, Task.Status.REVIEWING)
        # No notification should be sent
        self.assertEqual(len(self.mail.inbox), 0)

        _validate_slack_messages('Task is under review.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        # Reviewer rejects task
        task = submit_task(task.id, {}, Iteration.Status.PROVIDED_REVIEW,
                           self.workers[1])
        self.assertEqual(task.status, Task.Status.POST_REVIEW_PROCESSING)
        # Notification should be sent to original worker
        self.assertEqual(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEqual(notification['recipient'],
                         self.workers[0].user.email)
        self.assertEqual(notification['subject'],
                         'Your task has been returned')

        _validate_slack_messages('Task was returned by reviewer.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        # Entry-level worker resubmits task
        task = submit_task(task.id, {}, Iteration.Status.REQUESTED_REVIEW,
                           self.workers[0])
        self.assertEqual(task.status, Task.Status.REVIEWING)
        # Notification should be sent to reviewer
        self.assertEqual(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEqual(notification['recipient'],
                         self.workers[1].user.email)
        self.assertEqual(notification['subject'],
                         'A task is ready for re-review!')

        _validate_slack_messages('Task is under review.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        # First reviewer accepts task
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=True):
            task = submit_task(task.id, {}, Iteration.Status.REQUESTED_REVIEW,
                               self.workers[1])
        self.assertEqual(task.status, Task.Status.PENDING_REVIEW)
        # Notification should be sent to first reviewer
        self.assertEqual(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEqual(notification['recipient'],
                         self.workers[1].user.email)
        self.assertEqual(notification['subject'],
                         'Your task is under review!')

        _validate_slack_messages('Task is awaiting review.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        # Second reviewer picks up task
        task = assign_task(self.workers[3].id, task.id)
        self.assertEqual(task.status, Task.Status.REVIEWING)
        # No notification should be sent
        self.assertEqual(len(self.mail.inbox), 0)

        _validate_slack_messages('Task is under review.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        # Second reviewer rejects task
        task = submit_task(task.id, {}, Iteration.Status.PROVIDED_REVIEW,
                           self.workers[3])
        self.assertEqual(task.status, Task.Status.POST_REVIEW_PROCESSING)
        # Notification should be sent to first reviewer
        self.assertEqual(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEqual(notification['recipient'],
                         self.workers[1].user.email)
        self.assertEqual(notification['subject'],
                         'Your task has been returned')

        _validate_slack_messages('Task was returned by reviewer.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        # First reviewer resubmits task
        task = submit_task(task.id, {}, Iteration.Status.REQUESTED_REVIEW,
                           self.workers[1])
        self.assertEqual(task.status, Task.Status.REVIEWING)
        # Notification should be sent to second reviewer
        self.assertEqual(len(self.mail.inbox), 1)
        notification = self.mail.inbox.pop()
        self.assertEqual(notification['recipient'],
                         self.workers[3].user.email)
        self.assertEqual(notification['subject'],
                         'A task is ready for re-review!')

        _validate_slack_messages('Task is under review.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        # Second reviewer accepts task; task is complete
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            task = submit_task(task.id, {}, Iteration.Status.REQUESTED_REVIEW,
                               self.workers[3])
        self.assertEqual(task.status, Task.Status.COMPLETE)

        # Notification should be sent to all workers on task
        self.assertEqual(len(self.mail.inbox), 3)
        recipients = {mail['recipient'] for mail in self.mail.inbox}
        subjects = {mail['subject'] for mail in self.mail.inbox}
        self.assertEqual(recipients,
                         {self.workers[uid].user.email for uid in (0, 1, 3)})
        self.assertEqual(subjects, {'Task complete!'})
        self.mail.clear()

        _validate_slack_messages('Task has been completed.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        # Pause the project
        status_choices = dict(Project.STATUS_CHOICES)
        paused_status = status_choices[Project.Status.PAUSED]

        set_project_status(task.project.id, paused_status)
        task.project.refresh_from_db()
        _validate_slack_messages('has been paused.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        self.assertEqual(task.project.status, Project.Status.PAUSED)

        # Unpause the project
        active_status = status_choices[Project.Status.ACTIVE]
        set_project_status(task.project.id, active_status)
        task.project.refresh_from_db()
        _validate_slack_messages('has been reactivated.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

        self.assertEqual(task.project.status, Project.Status.ACTIVE)

        # End project
        end_project(task.project.id)
        task = Task.objects.get(id=task.id)
        self.assertEqual(task.status, Task.Status.ABORTED)

        # Notification should be sent to all workers on task
        self.assertEqual(len(self.mail.inbox), 3)
        recipients = {mail['recipient'] for mail in self.mail.inbox}
        subjects = {mail['subject'] for mail in self.mail.inbox}
        self.assertEqual(recipients,
                         {self.workers[uid].user.email for uid in (0, 1, 3)})
        self.assertEqual(subjects,
                         {'A task you were working on has been ended'})
        self.mail.clear()

        for task in project.tasks.all():
            _validate_slack_messages((
                '*Project {} | {} has been aborted.*\n'
                ).format(
                    task.project.workflow_version.slug,
                    task.project.short_description))
            _validate_slack_messages('Task has been aborted.')
        self.assertEqual(len(internal_slack_messages), 0)
        self.assertEqual(len(experts_slack_messages), 0)

    def test_slack_group_id(self):
        def fake_random_string():
            fake_random_string.num_calls = (
                getattr(fake_random_string, 'num_calls', 0) + 1)
            return str(fake_random_string.num_calls)

        for group_name in ('ketchup-3-sales-1', 'bongo-bash723581-3',
                           'bongo-bash723581-4'):
            self.slack.conversations.create(group_name, is_private=True)

        project = self.projects['reject_rev_proj']

        # Ensure slack group names are properly slugified and randomized.
        project.short_description = "Sally's Plumbing Emporium | Write Copy"
        group_name = _project_slack_group_name(project)
        self.assertTrue(group_name.startswith('sallys-plumbing'))
        self.assertEqual(len(group_name), 20)

        # Ensure slack group names are properly slugified and randomized.
        project.short_description = "Sally's Plumbingorama Emporium | Write"
        group_name = _project_slack_group_name(project)
        self.assertTrue(group_name.startswith('sallys-plumbingo'))
        self.assertEqual(len(group_name), 21)

        # Test that we create unique slack IDs if there are conflicts by
        # mocking the randomization logic to return deterministic results and
        # ensure that we don't repeat project IDs.
        patch_path = 'orchestra.communication.slack._random_string'
        with patch(patch_path, new=fake_random_string):
            for short_description, group_id in (
                    # Because the mock function's counter is at 1 and
                    # ketchup-3-sales-1 already exists, the channel gets set
                    # to ketchup-3-sales-2.
                    ('ketchup #3 Sales --:/ kitchen supplies',
                     'ketchup-3-sales-2'),
                    # Because the mock function's counter is at 3 and bongo-
                    # bash723581-3 / bongo-bash723581-4 already exist, the
                    # channel gets set to bongo-bash723581-5.
                    ('!!bongo bash*&#$(*$7235818923701842312',
                     'bongo-bash723581-5'),
                    ('shortie', 'shortie-6'),
                    ('what a treat!', 'what-a-treat-7'),
                    ('what a treat!', 'what-a-treat-8'),
                    ('what a treat!', 'what-a-treat-9'),
                    ("Sally's Plumbing Emporium", 'sallys-plumbing-10')):
                project.short_description = short_description
                self.assertEqual(_project_slack_group_name(project), group_id)
