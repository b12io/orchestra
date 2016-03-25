from orchestra.models import WorkerCertification
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import CertificationFactory
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.tests.helpers.fixtures import WorkerCertificationFactory
from orchestra.tests.helpers.fixtures import WorkflowFactory
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.workflow.certifications import migrate_certifications


class ManageCertificationsTestCase(OrchestraTestCase):
    def setUp(self):
        self.workflow_old = WorkflowFactory(
            slug='workflow_old',
            name='Old workflow',
            description='Old workflow to migrate certifications from.',
            code_directory='workflow_old')
        self.workflow_new = WorkflowFactory(
            slug='workflow_new',
            name='New workflow',
            description='New workflow to migrate certifications from.',
            code_directory='workflow_new')

        for workflow in (self.workflow_old, self.workflow_new):
            # Certifications must exist in both workflows for certification
            # to be migrated
            CertificationFactory(
                slug='certification1',
                name='Certification 1',
                description='First certification to migrate.',
                workflow=workflow)
            CertificationFactory(
                slug='certification2',
                name='Certification 2',
                description='Second certification to migrate.',
                workflow=workflow)

        user = (UserFactory(username='test',
                            first_name='test',
                            last_name='test',
                            password='test',
                            email='test@test.com'))
        self.worker = WorkerFactory(user=user)

        for certification in self.workflow_old.certifications.all():
            # Worker certifications exist only for old workflow
            WorkerCertificationFactory(
                worker=self.worker,
                certification=certification,
                role=WorkerCertification.Role.ENTRY_LEVEL)
            WorkerCertificationFactory(
                worker=self.worker,
                certification=certification,
                role=WorkerCertification.Role.REVIEWER)

        super().setUp()

    def test_migrate_certifications(self):
        def _check_old_certifications_unchanged():
            self.assertEquals(WorkerCertification.objects.filter(
                worker=self.worker,
                certification__workflow=self.workflow_old).count(), 4)
            self.assertEquals(WorkerCertification.objects.filter(
                worker=self.worker,
                certification__workflow=self.workflow_old,
                certification__slug='certification1',
                role=WorkerCertification.Role.ENTRY_LEVEL).count(), 1)
            self.assertEquals(WorkerCertification.objects.filter(
                worker=self.worker,
                certification__workflow=self.workflow_old,
                certification__slug='certification1',
                role=WorkerCertification.Role.REVIEWER).count(), 1)
            self.assertEquals(WorkerCertification.objects.filter(
                worker=self.worker,
                certification__workflow=self.workflow_old,
                certification__slug='certification2',
                role=WorkerCertification.Role.ENTRY_LEVEL).count(), 1)
            self.assertEquals(WorkerCertification.objects.filter(
                worker=self.worker,
                certification__workflow=self.workflow_old,
                certification__slug='certification2',
                role=WorkerCertification.Role.REVIEWER).count(), 1)

        _check_old_certifications_unchanged()
        # New workflow should have no worker certifications
        self.assertEquals(WorkerCertification.objects.filter(
            worker=self.worker,
            certification__workflow=self.workflow_new).count(), 0)

        # Migrate `certification1`
        migrate_certifications(
            self.workflow_old.slug,
            self.workflow_new.slug,
            ['certification1'])

        _check_old_certifications_unchanged()

        # New workflow should have only `certification1` worker certifications
        self.assertEquals(WorkerCertification.objects.filter(
            worker=self.worker,
            certification__workflow=self.workflow_new).count(), 2)
        self.assertEquals(WorkerCertification.objects.filter(
            worker=self.worker,
            certification__workflow=self.workflow_new,
            certification__slug='certification1',
            role=WorkerCertification.Role.ENTRY_LEVEL).count(), 1)
        self.assertEquals(WorkerCertification.objects.filter(
            worker=self.worker,
            certification__workflow=self.workflow_new,
            certification__slug='certification1',
            role=WorkerCertification.Role.REVIEWER).count(), 1)

        # Migrate all source certifications
        migrate_certifications(
            self.workflow_old.slug,
            self.workflow_new.slug,
            [])

        _check_old_certifications_unchanged()

        # `certification2` should now be migrated as well
        self.assertEquals(WorkerCertification.objects.filter(
            worker=self.worker,
            certification__workflow=self.workflow_new).count(), 4)
        self.assertEquals(WorkerCertification.objects.filter(
            worker=self.worker,
            certification__workflow=self.workflow_new,
            certification__slug='certification1',
            role=WorkerCertification.Role.ENTRY_LEVEL).count(), 1)
        self.assertEquals(WorkerCertification.objects.filter(
            worker=self.worker,
            certification__workflow=self.workflow_new,
            certification__slug='certification1',
            role=WorkerCertification.Role.REVIEWER).count(), 1)
        self.assertEquals(WorkerCertification.objects.filter(
            worker=self.worker,
            certification__workflow=self.workflow_new,
            certification__slug='certification2',
            role=WorkerCertification.Role.ENTRY_LEVEL).count(), 1)
        self.assertEquals(WorkerCertification.objects.filter(
            worker=self.worker,
            certification__workflow=self.workflow_new,
            certification__slug='certification2',
            role=WorkerCertification.Role.REVIEWER).count(), 1)
