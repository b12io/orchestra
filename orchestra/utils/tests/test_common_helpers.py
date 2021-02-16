from django.test import TestCase
from unittest.mock import patch

from orchestra.models import Todo
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.utils.common_helpers import get_update_message
from orchestra.utils.common_helpers import notify_single_todo_update


class ViewHelpersTests(TestCase):
    def setUp(self):
        super().setUp()
        self.project = ProjectFactory()
        step = StepFactory()
        self.old_title = 'Old title'
        self.new_title = 'New title'
        self.old_details = 'Old details'
        self.new_details = 'New details'
        self.old_todo = TodoFactory(
            title=self.old_title,
            details=self.old_details,
            project=self.project,
            step=step)
        self.new_todo = TodoFactory(
            title=self.new_title,
            details=self.new_details,
            status=Todo.Status.COMPLETED.value,
            project=self.project,
            step=step)
        self.sender = UserFactory()

    def test_empty_msg_if_no_updates(self):
        old_todo = self.new_todo
        msg = get_update_message(old_todo, self.new_todo, self.sender)
        expected_msg = ''
        self.assertEqual(msg, expected_msg)

    def test_fields_updated_completed_with_sender(self):
        msg = get_update_message(self.old_todo, self.new_todo, self.sender)
        expected_msg = (
            '{} has updated `{}`: marked complete, '
            'changed title and details'
        ).format(self.sender.username, self.new_todo.title)
        self.assertEqual(msg, expected_msg)

        # Reversing the change
        msg = get_update_message(self.new_todo, self.old_todo, self.sender)
        expected_msg = (
            '{} has updated `{}`: marked incomplete, '
            'changed title and details'
        ).format(self.sender.username, self.old_todo.title)
        self.assertEqual(msg, expected_msg)

    def test_fields_updated_completed_without_sender(self):
        msg = get_update_message(self.old_todo, self.new_todo)
        expected_msg = (
            '`{}` has been updated: marked complete, '
            'changed title and details'
        ).format(self.new_todo.title)
        self.assertEqual(msg, expected_msg)

        # Reversing the change
        msg = get_update_message(self.new_todo, self.old_todo)
        expected_msg = (
            '`{}` has been updated: marked incomplete, '
            'changed title and details'
        ).format(self.old_todo.title)
        self.assertEqual(msg, expected_msg)

    def test_fields_not_updated_completed(self):
        new_todo = TodoFactory(
            title=self.old_title,
            details=self.old_details,
            status=Todo.Status.COMPLETED.value)
        msg = get_update_message(self.old_todo, new_todo, self.sender)
        expected_msg = '{} has updated `{}`: marked complete'.format(
            self.sender.username, new_todo.title)
        self.assertEqual(msg, expected_msg)

        # Reversing the change
        msg = get_update_message(new_todo, self.old_todo, self.sender)
        expected_msg = '{} has updated `{}`: marked incomplete'.format(
            self.sender.username, new_todo.title)
        self.assertEqual(msg, expected_msg)

    def test_fields_not_updated_not_relevant(self):
        new_todo = TodoFactory(
            title=self.old_title,
            details=self.old_details,
            status=Todo.Status.DECLINED.value)
        msg = get_update_message(self.old_todo, new_todo, self.sender)
        expected_msg = '{} has updated `{}`: marked not relevant'.format(
            self.sender.username, new_todo.title)
        self.assertEqual(msg, expected_msg)

        # No sender
        msg = get_update_message(self.old_todo, new_todo)
        expected_msg = '`{}` has been updated: marked not relevant'.format(
            new_todo.title)
        self.assertEqual(msg, expected_msg)

        # Reversing the change
        msg = get_update_message(new_todo, self.old_todo)
        expected_msg = '`{}` has been updated: marked relevant'.format(
            new_todo.title)
        self.assertEqual(msg, expected_msg)

    def test_fields_updated(self):
        old_todo = TodoFactory(
            title=self.old_title,
            details=self.old_details)
        new_todo = TodoFactory(
            title=self.new_title,
            details=self.new_details)
        msg = get_update_message(old_todo, new_todo, self.sender)
        expected_msg = (
            '{} has updated `{}`: changed title and details').format(
            self.sender.username, new_todo.title)
        self.assertEqual(msg, expected_msg)

        # Only title has changed
        old_todo = TodoFactory(
            title=self.old_title,
            details=self.old_details)
        new_todo = TodoFactory(
            title=self.new_title,
            details=self.old_details)
        msg = get_update_message(old_todo, new_todo, self.sender)
        expected_msg = (
            '{} has updated `{}`: changed title').format(
            self.sender.username, new_todo.title)
        self.assertEqual(msg, expected_msg)

    @patch('orchestra.utils.common_helpers.message_experts_slack_group')
    def test_notify_single_todo_update(self, mock_slack):
        # Level 0 todos
        WorkerFactory(user=self.sender)
        notify_single_todo_update(
            self.sender, self.old_todo, self.new_todo)
        self.assertEqual(mock_slack.call_count, 1)

        # Level 1 todos
        parent_todo_level_1 = TodoFactory(title='Parent todo')
        old_todo = TodoFactory(
            title=self.old_title,
            parent_todo=parent_todo_level_1,
            project=self.project,
            details=self.old_details)
        new_todo = TodoFactory(
            title=self.new_title,
            parent_todo=parent_todo_level_1,
            project=self.project,
            details=self.new_details)

        notify_single_todo_update(self.sender, old_todo, new_todo)
        self.assertEqual(mock_slack.call_count, 2)

        # Level 2 todos
        parent_todo_level_2 = TodoFactory(
            title='Parent todo',
            parent_todo=parent_todo_level_1)
        old_todo = TodoFactory(
            title=self.old_title,
            parent_todo=parent_todo_level_2,
            project=self.project,
            details=self.old_details)
        new_todo = TodoFactory(
            title=self.new_title,
            parent_todo=parent_todo_level_2,
            project=self.project,
            details=self.new_details)

        notify_single_todo_update(self.sender, old_todo, new_todo)
        self.assertEqual(mock_slack.call_count, 2)
