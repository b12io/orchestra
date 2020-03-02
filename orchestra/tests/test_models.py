import datetime

from dateutil.parser import parse

from orchestra.accounts.signals import orchestra_user_registered
from orchestra.core.errors import ModelSaveError
from orchestra.models import PayRate
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.tests.helpers import OrchestraModelTestCase
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import CertificationFactory
from orchestra.tests.helpers.fixtures import PayRateFactory
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import TaskAssignmentFactory
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import WorkerCertificationFactory
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.tests.helpers.fixtures import WorkflowFactory
from orchestra.tests.helpers.fixtures import WorkflowVersionFactory
from orchestra.tests.helpers.fixtures import setup_models


class ModelsTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.workers[0] = Worker.objects.get(user__username='test_user_1')
        self.worker = self.workers[0]

    def test_certification_roles(self):
        """ Ensure that workers can be certified at multiple roles. """
        certification = CertificationFactory(
            slug='cat_herding', name='Cat herding',
            workflow=self.workflows['w1'])
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
            slug='cat_herding', name='Cat herding',
            workflow=self.workflows['w1'])
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
        orchestra_user_registered.send(
            sender=self.__class__, user=user, request=None)

        # Expect the worker object to be created
        self.assertTrue(Worker.objects.filter(user=user).exists(),
                        'Worker not autocreated on User registration')

    def test_pay_rate_creation(self):
        """
        Ensure that PayRates are created with valid ranges and do not
        overlap with existing entries.
        """
        start_stop_dates = [
            (('2016-01-01', '2016-01-03'), ('2016-01-02', None), False),
            (('2016-01-01', None), ('2016-02-01', None), False),
            (('2016-01-01', None), ('2015-12-01', '2016-01-01'), False),
            (('2016-01-01', '2016-01-10'), ('2016-01-03', '2016-01-08'),
             False),
            (('2016-01-01', '2016-01-10'), ('2015-12-30', '2016-01-03'),
             False),
            (('2016-01-01', '2016-01-10'), ('2016-01-03', '2016-01-18'),
             False),
            (('2016-01-01', '2016-01-10'), ('2015-12-30', '2016-01-18'),
             False),
            (('2016-01-01', '2016-01-10'), ('2016-01-30', None), True),
            (('2016-01-01', '2016-01-10'), ('2016-01-30', '2016-02-18'), True),
            (('2016-03-02', None), ('2016-01-01', '2016-03-01'), True)
        ]

        def _parse_date(date):
            if date:
                start_date = parse(date).date()
            else:
                start_date = None
            return start_date

        def _verify_failure(saved, new, success):
            start_date_saved = _parse_date(saved[0])
            end_date_saved = _parse_date(saved[1])
            PayRate.objects.create(worker=self.worker,
                                   hourly_rate=10,
                                   hourly_multiplier=1.2,
                                   start_date=start_date_saved,
                                   end_date=end_date_saved)
            start_date_new = _parse_date(new[0])
            end_date_new = _parse_date(new[1])
            payrate = PayRate(worker=self.worker,
                              hourly_rate=10,
                              hourly_multiplier=1.2,
                              start_date=start_date_new,
                              end_date=end_date_new)
            if success:
                payrate.save()
            else:
                with self.assertRaises(ModelSaveError):
                    payrate.save()
            PayRate.objects.all().delete()

        for saved, new, success in start_stop_dates:
            _verify_failure(saved, new, success)

    def test_pay_rate_update(self):
        """ Verify that we don't detect overlap collision with itself. """
        payrate = PayRate.objects.create(
            worker=self.worker,
            hourly_rate=10,
            hourly_multiplier=1.2,
            start_date=datetime.date(2016, 1, 1),
            end_date=None)
        payrate.end_date = datetime.date(2016, 3, 1)
        payrate.save()


class CertificationTestCase(OrchestraModelTestCase):
    __test__ = True
    model = CertificationFactory


class StepTestCase(OrchestraModelTestCase):
    __test__ = True
    model = StepFactory


class PayRateTestCase(OrchestraModelTestCase):
    __test__ = True
    model = PayRateFactory


class ProjectTestCase(OrchestraModelTestCase):
    __test__ = True
    model = ProjectFactory


class TaskTestCase(OrchestraModelTestCase):
    __test__ = True
    model = TaskFactory

    def test_get_detailed_description(self):
        """
        Verify that the detailed description text is valid
        """
        # description functions are optional
        task = TaskFactory()
        self.assertEqual(task.get_detailed_description(), '')

        no_kwargs = {
            'path': ('orchestra.tests.helpers.'
                     'fixtures.get_detailed_description')
        }
        task_no_kwargs = TaskFactory(
            step=StepFactory(slug='stepslug',
                             detailed_description_function=no_kwargs))
        self.assertEqual(task_no_kwargs.get_detailed_description(),
                         'No text given stepslug')

        with_kwargs = {
            'path': ('orchestra.tests.helpers.'
                     'fixtures.get_detailed_description'),
            'kwargs': {
                'text': 'task 2 text',
            }
        }
        task_with_kwargs = TaskFactory(
            step=StepFactory(slug='stepslug',
                             detailed_description_function=with_kwargs))
        self.assertEqual(task_with_kwargs.get_detailed_description(),
                         'task 2 text stepslug')

        extra_kwargs = {'text': 'extra text'}
        self.assertEqual(
            task_with_kwargs.get_detailed_description(
                extra_kwargs=extra_kwargs),
            'extra text stepslug'
        )


class TaskAssignmentTestCase(OrchestraModelTestCase):
    __test__ = True
    model = TaskAssignmentFactory


class WorkerTestCase(OrchestraModelTestCase):
    __test__ = True
    model = WorkerFactory

    def setUp(self):
        self.cert = CertificationFactory()
        super().setUp()

    def test_is_reviewer(self):
        worker = WorkerFactory()
        WorkerCertificationFactory(
            worker=worker,
            certification=self.cert,
            role=WorkerCertification.Role.ENTRY_LEVEL)
        WorkerCertificationFactory(
            worker=worker,
            certification=self.cert,
            role=WorkerCertification.Role.REVIEWER)
        self.assertTrue(worker.is_reviewer(self.cert))
        self.assertTrue(worker.is_entry_level(self.cert))

    def test_is_entry_level(self):
        worker = WorkerFactory()
        WorkerCertificationFactory(
            worker=worker,
            certification=self.cert,
            role=WorkerCertification.Role.ENTRY_LEVEL)
        self.assertTrue(worker.is_entry_level(self.cert))
        self.assertFalse(worker.is_reviewer(self.cert))


class WorkerCertificationTestCase(OrchestraModelTestCase):
    __test__ = True
    model = WorkerCertificationFactory


class WorkflowTestCase(OrchestraModelTestCase):
    __test__ = True
    model = WorkflowFactory


class WorkflowVersionTestCase(OrchestraModelTestCase):
    __test__ = True
    model = WorkflowVersionFactory
