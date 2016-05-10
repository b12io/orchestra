from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError

from orchestra.tests.helpers import OrchestraTestCase


class MigrateCertificationsTestCase(OrchestraTestCase):
    patch_path = ('orchestra.management.commands.'
                  'migrate_certifications.migrate_certifications')

    @patch(patch_path)
    def test_options(self, mock_migrate):
        # Test no options
        with self.assertRaises(CommandError):
            call_command('migrate_certifications')
            mock_migrate.assert_not_called()

        # Test
        call_command('migrate_certifications',
                     'test_source_workflow_slug',
                     'ntest_destination_workflow_slug',
                     certifications=['test_cert_1', 'test_cert_2'])
        mock_migrate.called_once_with(
            'test_source_workflow_slug',
            'test_destination_workflow_slug',
            ['test_cert_1', 'test_cert_2']
        )
