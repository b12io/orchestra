from django.test import TestCase
from django.utils import timezone

from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import TodoFactory
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.utils.common_helpers import get_update_message


class ViewHelpersTests(TestCase):
    def setUp(self):
        super().setUp()
        project = ProjectFactory()
        step = StepFactory()
        self.old_title = 'Old title'
        self.new_title = 'New title'
        self.old_details = 'Old details'
        self.new_details = 'New details'
        self.old_todo = TodoFactory(
            title=self.old_title,
            details=self.old_details,
            completed=False,
            project=project,
            step=step)
        self.new_todo = TodoFactory(
            title=self.new_title,
            details=self.new_details,
            completed=True,
            project=project,
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

    def test_fields_updated_completed_without_sender(self):
        msg = get_update_message(self.old_todo, self.new_todo)
        expected_msg = (
            '`{}` has been updated: marked complete, '
            'changed title and details'
            ).format(self.new_todo.title)
        self.assertEqual(msg, expected_msg)

    def test_fields_not_updated_completed(self):
        new_todo = TodoFactory(
            title=self.old_title,
            details=self.old_details,
            completed=True)
        msg = get_update_message(self.old_todo, new_todo, self.sender)
        expected_msg = '{} has updated `{}`: marked complete'.format(
            self.sender.username, new_todo.title)
        self.assertEqual(msg, expected_msg)

    def test_fields_not_updated_not_relevant(self):
        new_todo = TodoFactory(
            title=self.old_title,
            details=self.old_details,
            completed=False,
            skipped_datetime=timezone.now())
        msg = get_update_message(self.old_todo, new_todo, self.sender)
        expected_msg = '{} has updated `{}`: marked not relevant'.format(
            self.sender.username, new_todo.title)
        self.assertEqual(msg, expected_msg)

        # No sender
        msg = get_update_message(self.old_todo, new_todo)
        expected_msg = '`{}` has been updated: marked not relevant'.format(
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
