from unittest.mock import patch

from django.forms.models import model_to_dict
from django.test import override_settings
from django.utils import timezone

from orchestra.admin.forms import TaskForm
from orchestra.core.errors import WorkerCertificationError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import ProjectFactory
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import submit_task
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import is_worker_assigned_to_task


class AdminTestCase(OrchestraTestCase):

    def setUp(self):
        super(AdminTestCase, self).setUp()
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

        project = self.projects['test_human_and_machine']
        self.assertEquals(Task.objects.filter(project=project).count(), 0)
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

    def test_task_form_save(self):
        """
        Test task form save for new, human and machine tasks
        """
        workflow_version = self.workflow_versions['test_workflow']
        human_step = self.workflow_steps[workflow_version.slug]['step1']
        project = ProjectFactory(workflow_version=workflow_version)

        # Add new task to project
        form = TaskForm({'project': project.id,
                         'status': Task.Status.AWAITING_PROCESSING,
                         'step': human_step.id,
                         'start_datetime': timezone.now()})
        form.is_valid()
        self.assertTrue(form.is_valid())
        task = form.save()
        self.assertFalse(task.assignments.exists())

        # Add new task to project and assign to entry_level worker (0)
        form = TaskForm({'project': project.id,
                         'status': Task.Status.AWAITING_PROCESSING,
                         'step': human_step.id,
                         'start_datetime': timezone.now()})
        self.assertTrue(form.is_valid())
        form.cleaned_data['currently_assigned_to'] = self.workers[0].id
        task = form.save()
        self.assertTrue(is_worker_assigned_to_task(self.workers[0],
                                                   task))
        self.assertEquals(assignment_history(task).count(), 1)
        self.assertTrue(task.assignments.exists())
        self.assertEquals(task.status, Task.Status.PROCESSING)

        # Render task with preexisting entry_level assignment (0) and reassign
        # to another entry_level worker (4)
        form = TaskForm(model_to_dict(task), instance=task)
        self.assertEquals(form.fields['currently_assigned_to'].initial,
                          self.workers[0].id)
        form.is_valid()
        self.assertTrue(form.is_valid())
        form.cleaned_data['currently_assigned_to'] = self.workers[4].id
        task = form.save()
        self.assertTrue(is_worker_assigned_to_task(self.workers[4],
                                                   task))
        self.assertEquals(assignment_history(task).count(), 1)
        self.assertEquals(task.status, Task.Status.PROCESSING)

        # Submit task
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=True):
            task = submit_task(task.id, {},
                               TaskAssignment.SnapshotType.SUBMIT,
                               self.workers[4], 0)

        # Assign to reviewer (1) and reassign to another reviewer (3)
        task = assign_task(self.workers[1].id, task.id)
        self.assertTrue(task.status, Task.Status.REVIEWING)
        self.assertTrue(is_worker_assigned_to_task(self.workers[1],
                                                   task))
        task = Task.objects.get(id=task.id)
        form = TaskForm(model_to_dict(task), instance=task)
        self.assertEquals(form.fields['currently_assigned_to'].initial,
                          self.workers[1].id)
        self.assertTrue(form.is_valid())
        form.cleaned_data['currently_assigned_to'] = self.workers[3].id
        task = form.save()
        self.assertTrue(is_worker_assigned_to_task(self.workers[3],
                                                   task))
        self.assertEquals(assignment_history(task).count(), 2)
        self.assertEquals(task.status, Task.Status.REVIEWING)

        # Attempt to reassign to non-certified worker (2)
        form = TaskForm(model_to_dict(task), instance=task)
        self.assertTrue(form.is_valid())
        form.cleaned_data['currently_assigned_to'] = self.workers[2].id
        with self.assertRaises(WorkerCertificationError):
            form.save()
