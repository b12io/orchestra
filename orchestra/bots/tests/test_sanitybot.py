from collections import Counter
from datetime import timedelta
from unittest.mock import patch

from orchestra.bots.sanitybot import create_and_handle_sanity_checks
from orchestra.models import SanityCheck
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.task_lifecycle import create_subsequent_tasks


class SanityBotTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)

    @patch('orchestra.bots.sanitybot.message_experts_slack_group')
    def test_create_and_handle_sanity_checks(self, mock_slack):
        # Initialize relevant project.
        create_subsequent_tasks(self.projects['sanitybot'])
        # Initialize irrelevant project.
        create_subsequent_tasks(self.projects['test_human_and_machine'])

        # No sanity checks exist, and Slack hasn't received a message.
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(sanity_checks.count(), 0)
        self.assertEqual(mock_slack.call_count, 0)

        create_and_handle_sanity_checks()
        # Of the four sanity checks for this project, three were
        # triggered by orchestra.tests.helpers.workflow.check_project.
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(
            dict(Counter(sanity_checks.values_list('check_slug', flat=True))),
            {
                'frequently_repeating_check': 1,
                'infrequently_repeating_check': 1,
                'onetime_check': 1
            })
        for sanity_check in sanity_checks:
            self.assertEqual(
                sanity_check.project.workflow_version.slug,
                'sanitybot_workflow')
        # Three slack messages for three sanity checks.
        self.assertEqual(mock_slack.call_count, 3)

        # Too little time has passed, so we expect no new sanity checks.
        create_and_handle_sanity_checks()
        # Still only three sanity check exists for the relevant project.
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(sanity_checks.count(), 3)
        # Slack didn't get called again.
        self.assertEqual(mock_slack.call_count, 3)

        # Mark the sanity checks as having happened two days ago. Only
        # the `frequently_repeating_check` should trigger.
        for sanity_check in sanity_checks:
            sanity_check.created_at = (
                sanity_check.created_at - timedelta(days=2))
            sanity_check.save()
        create_and_handle_sanity_checks()
        # Look for the three old sanity checks and a new
        # `frequently_repeating_check`.
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(
            dict(Counter(sanity_checks.values_list('check_slug', flat=True))),
            {
                'frequently_repeating_check': 2,
                'infrequently_repeating_check': 1,
                'onetime_check': 1
            })
        for sanity_check in sanity_checks:
            self.assertEqual(
                sanity_check.project.workflow_version.slug,
                'sanitybot_workflow')
        # Slack got called another time.
        self.assertEqual(mock_slack.call_count, 4)

        create_and_handle_sanity_checks()
        # Still only four sanity checks exists for the relevant project.
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(sanity_checks.count(), 4)
        # Slack didn't get called again.
        self.assertEqual(mock_slack.call_count, 4)
