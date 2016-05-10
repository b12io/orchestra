from io import StringIO

from django.core.management import call_command

from orchestra.tests.helpers import OrchestraTestCase


class LoadAllWorkflowsTestCase(OrchestraTestCase):

    def test_options(self):
        # Initial load should work
        stderr1 = StringIO()
        call_command('loadallworkflows', stderr=stderr1)
        output1 = stderr1.getvalue()
        self.assertNotIn('error', output1)

        # Now it works
        stderr2 = StringIO()
        call_command('loadallworkflows', force=True, stderr=stderr2)
        output2 = stderr2.getvalue()
        self.assertNotIn('error', output2)
