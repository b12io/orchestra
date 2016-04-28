from orchestra.models import CommunicationPreference
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import WorkerFactory


class ManagersTestCase(OrchestraTestCase):

    def setUp(self):
        self.user = UserFactory()
        self.worker = WorkerFactory(user=self.user)
        super().setUp()

    def test_get_or_create_all_types(self):
        comm_prefs = CommunicationPreference.objects.get_or_create_all_types(
            self.worker)
        comm_types = CommunicationPreference.CommunicationType.choices()
        self.assertEqual(len(comm_prefs), len(comm_types))
        for comm_type, _ in comm_types:
            comm_pref = CommunicationPreference.objects.get(
                communication_type=comm_type,
                worker=self.worker)
            for key, is_set in comm_pref.methods.iteritems():
                self.assertTrue(is_set)

    def test_get_or_create_all_types_set_methods(self):
        """
            Manually set the desired methods that are allowed.
        """

        methods = ~CommunicationPreference.methods.email
        methods &= CommunicationPreference.methods.slack
        comm_prefs = CommunicationPreference.objects.get_or_create_all_types(
            self.worker, methods=methods)
        comm_types = CommunicationPreference.CommunicationType.choices()
        self.assertEqual(len(comm_prefs), len(comm_types))
        for comm_type, _ in comm_types:
            comm_pref = CommunicationPreference.objects.get(
                communication_type=comm_type,
                worker=self.worker)
            self.assertTrue(comm_pref.methods.slack)
            self.assertFalse(comm_pref.methods.email)
