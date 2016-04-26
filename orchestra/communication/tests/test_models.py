from orchestra.accounts.signals import orchestra_user_registered
from orchestra.models import CommunicationPreference
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import WorkerFactory


class ModelsTestCase(OrchestraTestCase):

    def test_get_communication_type_description(self):
        # Create a user
        user = UserFactory(username='test_registration_user',
                           password='test',
                           email='test_registration_user@test.com')

        worker = WorkerFactory(user=user)
        type_ = CommunicationPreference.CommunicationType.TASK_STATUS_CHANGE
        comm_preference = CommunicationPreference.objects.create(
            worker=worker,
            communication_type=type_.value
        )

        self.assertEqual(
            comm_preference.get_comunication_type_description(),
            'task_status_change'
        )

    def test_communication_preference_autocreation(self):
        """
            When new users register, CommunicationPreferences should be
            automatically created .
        """

        # Create a user
        user = UserFactory(username='test_registration_user',
                           password='test',
                           email='test_registration_user@test.com')

        # There should be no preferences yet
        self.assertFalse(CommunicationPreference.objects.filter(
            worker__user=user).exists())

        # Fake registering the user
        orchestra_user_registered.send(
            sender=self.__class__, user=user, request=None)

        # Expect the worker object to be created
        self.assertTrue(
            CommunicationPreference.objects.filter(worker__user=user).exists(),
            'CommunicationPreference not autocreated on User registration'
        )

        for comm_pref in CommunicationPreference.objects.all():
            for label, flag in comm_pref.methods.iteritems():
                self.assertTrue(flag)
