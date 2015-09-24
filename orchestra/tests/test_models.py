from registration.signals import user_registered

from orchestra.core.errors import ModelSaveError
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import CertificationFactory
from orchestra.tests.helpers.fixtures import WorkerCertificationFactory
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import setup_models


class ModelsTestCase(OrchestraTestCase):

    def setUp(self):
        super(ModelsTestCase, self).setUp()
        setup_models(self)
        self.workers[0] = Worker.objects.get(user__username='test_user_1')

    def test_certification_roles(self):
        """ Ensure that workers can be certified at multiple roles. """
        certification = CertificationFactory(
            slug='cat_herding', name='Cat herding')
        WorkerCertificationFactory(
            certification=certification,
            worker=self.workers[0],
            role=WorkerCertification.Role.ENTRY_LEVEL)
        WorkerCertificationFactory(
            certification=certification,
            worker=self.workers[0],
            role=WorkerCertification.Role.REVIEWER)

    def test_reviewer_requires_entry_level(self):
        """ Workers must have entry-level certification before they review. """
        certification = CertificationFactory(
            slug='cat_herding', name='Cat herding')
        with self.assertRaises(ModelSaveError):
            WorkerCertificationFactory(
                certification=certification,
                worker=self.workers[0],
                role=WorkerCertification.Role.REVIEWER)

    def test_worker_autocreation(self):
        """ When new users register, worker objects should be autocreated. """

        # Create a user
        user = UserFactory(username='test_registration_user',
                           password='test',
                           email='test_registration_user@test.com')

        # There should be no worker yet
        self.assertFalse(Worker.objects.filter(user=user).exists())

        # Fake registering the user
        user_registered.send(sender=self.__class__, user=user, request=None)

        # Expect the worker object to be created
        self.assertTrue(Worker.objects.filter(user=user).exists(),
                        'Worker not autocreated on User registration')
