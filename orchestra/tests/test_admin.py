from unittest import skip
from unittest.mock import patch

from django.conf import settings
from django.forms.models import model_to_dict
from django.test import override_settings

from orchestra.admin.forms import TaskForm
from orchestra.core.errors import WorkerCertificationError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Project
from orchestra.models import WorkerCertification
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.tests.helpers.fixtures import CertificationFactory
from orchestra.tests.helpers.fixtures import WorkerCertificationFactory
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import submit_task
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import is_worker_assigned_to_task
from orchestra.workflow import get_workflows
from orchestra.workflow import Step

ORIGINAL_ORCHESTRA_PATHS = settings.ORCHESTRA_PATHS


class AdminTestCase(OrchestraTestCase):

    def setUp(self):
        super(AdminTestCase, self).setUp()
        # Can't put this in self.setUp since test workflows don't work for
        # the form save test (see comment below)
        setup_models(self)

    @override_settings(MACHINE_STEP_SCHEDULER=(
        'orchestra.utils.machine_step_scheduler',
        'SynchronousMachineStepScheduler'))
    def test_task_form_init(self):
        """
        Test task form initialization for new, human and machine tasks
        """
        # Create new task form
        # (Test form init with no task instance)
        TaskForm()

        project = Project.objects.get(workflow_slug='test_workflow_2')
        self.assertEquals(Task.objects.filter(project=project).count(),
                          0)
        create_subsequent_tasks(project)

        # Human task was created but not assigned
        # (Test form init with empty assignment history)
        self.assertEquals(Task.objects.filter(project=project).count(),
                          1)
        human_task = Task.objects.filter(project=project).first()
        form = TaskForm(instance=human_task)
        self.assertEquals(form.fields['currently_assigned_to'].initial,
                          None)

        # Human task assigned to entry_level worker
        # (Test form init with a single entry-level worker)
        human_task = assign_task(self.workers[0].id, human_task.id)
        form = TaskForm(instance=human_task)
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=True):
            human_task = submit_task(human_task.id, {},
                                     TaskAssignment.SnapshotType.SUBMIT,
                                     self.workers[0], 0)
        self.assertEquals(form.fields['currently_assigned_to'].initial,
                          self.workers[0].id)

        # Human task under review
        # (Test form init with both an entry-level worker and reviewer)
        human_task = assign_task(self.workers[1].id, human_task.id)
        form = TaskForm(instance=human_task)
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            human_task = submit_task(human_task.id, {},
                                     TaskAssignment.SnapshotType.ACCEPT,
                                     self.workers[1], 0)
        self.assertEquals(form.fields['currently_assigned_to'].initial,
                          self.workers[1].id)

        # Machine task was created
        # (Test form init with a machine task)
        self.assertEquals(Task.objects.filter(project=project).count(),
                          2)
        machine_task = (Task.objects.filter(project=project)
                                    .exclude(id=human_task.id).first())
        form = TaskForm(instance=machine_task)
        self.assertEquals(form.fields['currently_assigned_to'].initial,
                          None)

    @skip('Broken until workflows are in the DB or the admin is re-written')
    # TODO(jrbotros): combine the two tests in this test case, since the
    # following test just calls save in the same situations as the first.
    @override_settings(ORCHESTRA_PATHS=ORIGINAL_ORCHESTRA_PATHS)
    def test_task_form_save(self):
        """
        Test task form save for new, human and machine tasks
        """
        # Workflow steps are hard-coded on `choices` for `Project` models
        # regardless of `settings.py`.  Once we move workflows back into the
        # database, we should use the test workflows rather than the production
        # ones in `settings.py.`  Until then, the hack below suffices.
        workflows = get_workflows()
        test_workflow_slug = 'website_design'
        workflow = workflows[test_workflow_slug]
        human_steps = {step_slug: step
                       for step_slug, step in workflow.steps.items()
                       if step.worker_type == Step.WorkerType.HUMAN}
        step_slug, step = human_steps.popitem()
        project = ProjectFactory(workflow_slug=test_workflow_slug)
        for certification_slug in step.required_certifications:
            certification = CertificationFactory(slug=certification_slug)
            for uname in (0, 1, 3, 6):
                WorkerCertificationFactory(
                    certification=certification,
                    worker=self.workers[uname],
                    role=WorkerCertification.Role.ENTRY_LEVEL)
            for uname in (3, 6):
                WorkerCertificationFactory(
                    certification=certification,
                    worker=self.workers[uname],
                    role=WorkerCertification.Role.REVIEWER)

        # Add new task to project
        form = TaskForm({'project': project.id,
                         'status': Task.Status.AWAITING_PROCESSING,
                         'step_slug': step_slug})
        form.is_valid()
        self.assertTrue(form.is_valid())
        task = form.save()
        self.assertFalse(task.assignments.exists())

        # Add new task to project and assign to entry_level worker (0)
        form = TaskForm({'project': project.id,
                         'status': Task.Status.AWAITING_PROCESSING,
                         'step_slug': step_slug})
        self.assertTrue(form.is_valid())
        form.cleaned_data['currently_assigned_to'] = self.workers[0].id
        task = form.save()
        self.assertTrue(is_worker_assigned_to_task(self.workers[0],
                                                   task))
        self.assertEquals(assignment_history(task).count(), 1)
        self.assertTrue(task.assignments.exists())
        self.assertEquals(task.status, Task.Status.PROCESSING)

        # Render task with preexisting entry_level assignment (0) and reassign
        # to another entry_level worker (1)
        form = TaskForm(model_to_dict(task), instance=task)
        self.assertEquals(form.fields['currently_assigned_to'].initial,
                          self.workers[0].id)
        form.is_valid()
        self.assertTrue(form.is_valid())
        form.cleaned_data['currently_assigned_to'] = self.workers[1].id
        task = form.save()
        self.assertTrue(is_worker_assigned_to_task(self.workers[1],
                                                   task))
        self.assertEquals(assignment_history(task).count(), 1)
        self.assertEquals(task.status, Task.Status.PROCESSING)

        # Submit task
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=True):
            task = submit_task(task.id, {},
                               TaskAssignment.SnapshotType.SUBMIT,
                               self.workers[1], 0)

        # Assign to reviewer (3) and reassign to another reviewer (6)
        task = assign_task(self.workers[3].id, task.id)
        self.assertTrue(task.status, Task.Status.REVIEWING)
        self.assertTrue(is_worker_assigned_to_task(self.workers[3],
                                                   task))
        task = Task.objects.get(id=task.id)
        form = TaskForm(model_to_dict(task), instance=task)
        self.assertEquals(form.fields['currently_assigned_to'].initial,
                          self.workers[3].id)
        self.assertTrue(form.is_valid())
        form.cleaned_data['currently_assigned_to'] = self.workers[6].id
        task = form.save()
        self.assertTrue(is_worker_assigned_to_task(self.workers[6],
                                                   task))
        self.assertEquals(assignment_history(task).count(), 2)
        self.assertEquals(task.status, Task.Status.REVIEWING)

        # Attempt to reassign to non-certified worker (2)
        form = TaskForm(model_to_dict(task), instance=task)
        self.assertTrue(form.is_valid())
        form.cleaned_data['currently_assigned_to'] = self.workers[2].id
        with self.assertRaises(WorkerCertificationError):
            form.save()
