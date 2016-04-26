from orchestra.accounts.signals import orchestra_user_registered
from orchestra.models import CommunicationPreference
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import UserFactory


class ModelsTestCase(OrchestraTestCase):

    def test_communication_preference_autocreation(self):
        """
            When new users register, CommunicationPreferences should be
        automatically created .
        """

        # Create a user
        user = UserFactory(username='test_registration_user',
                           password='test',
                           email='test_registration_user@test.com')

        # There should be no worker yet
        self.assertFalse(CommunicationPreference.objects.filter(
            worker__user=user).exists())

        # Fake registering the user
        orchestra_user_registered.send(
            sender=self.__class__, user=user, request=None)

        # Expect the worker object to be created
        self.assertTrue(CommunicationPreference.objects.filter(worker__user=user).exists(),
                        'CommunicationPreference not autocreated on User registration')

        for comm_pref in CommunicationPreference.objects.all():
            for label, flag in comm_pref.methods.iteritems():
                self.assertTrue(flag)
