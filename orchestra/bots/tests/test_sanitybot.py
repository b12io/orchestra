from datetime import timedelta
from unittest.mock import patch

from orchestra.bots.sanitybot import create_and_handle_sanity_checks
from orchestra.models import SanityCheck
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models


class SanityBotTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)

    @patch('orchestra.bots.sanitybot.message_experts_slack_group')
    def test_create_and_handle_sanity_checks(self, mock_slack):
        # Initialize relevant project
        create_subsequent_tasks(self.projects['sanitybot'])
        # Initialize irrelevant project
        create_subsequent_tasks(self.projects['test_human_and_machine'])

        # No sanity checks exist
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(sanity_checks.count(), 0)

        create_and_handle_sanity_checks()
        # One sanity check exists for the relevant project
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(sanity_checks.count(), 1)
        sanity_check = sanity_checks.first()
        self.assertEqual(sanity_check.project.workflow_version.slug,
                         'sanitybot_workflow')
        # Slack got called once
        self.assertEqual(mock_slack.call_count, 1)

        create_and_handle_sanity_checks()
        # Still only one sanity check exists for the relevant project
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(sanity_checks.count(), 1)
        # Slack didn't get called
        self.assertEqual(mock_slack.call_count, 1)

        # Change created datetime of the sanity check. If it happened
        # more than a day ago, the workflow is configured to create
        # another sanity check.
        sanity_check.created_at = sanity_check.created_at - timedelta(days=2)
        sanity_check.save()
        create_and_handle_sanity_checks()
        # Two sanity checks exist for the relevant project
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(sanity_checks.count(), 2)
        for sanity_check in sanity_checks:
            self.assertEqual(
                sanity_check.project.workflow_version.slug,
                'sanitybot_workflow')
        # Slack got called twice
        self.assertEqual(mock_slack.call_count, 2)

        create_and_handle_sanity_checks()
        # Still only two sanity checks exists for the relevant project
        sanity_checks = SanityCheck.objects.all()
        self.assertEqual(sanity_checks.count(), 2)
        # Slack didn't get called
        self.assertEqual(mock_slack.call_count, 2)
