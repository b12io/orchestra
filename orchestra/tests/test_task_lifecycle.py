import json
from unittest.mock import patch

from orchestra.core.errors import IllegalTaskSubmission
from orchestra.core.errors import NoTaskAvailable
from orchestra.core.errors import AssignmentPolicyError
from orchestra.core.errors import ModelSaveError
from orchestra.core.errors import ReviewPolicyError
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import WorkerCertificationError
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import WorkerCertification
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.assignment_snapshots import empty_snapshots
from orchestra.utils.task_lifecycle import _worker_certified_for_task
from orchestra.utils.task_lifecycle import _check_worker_allowed_new_assignment
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import end_project
from orchestra.utils.task_lifecycle import get_new_task_assignment
from orchestra.utils.task_lifecycle import get_next_task_status
from orchestra.utils.task_lifecycle import get_task_overview_for_worker
from orchestra.utils.task_lifecycle import submit_task
from orchestra.utils.task_lifecycle import task_history_details
from orchestra.utils.task_lifecycle import worker_assigned_to_rejected_task
from orchestra.utils.task_lifecycle import worker_has_reviewer_status
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import current_assignment
from orchestra.utils.task_properties import is_worker_assigned_to_task
from orchestra.workflow import get_workflow_by_slug
from orchestra.workflow import Step


class BasicTaskLifeCycleTestCase(OrchestraTestCase):
    """
    Test modular functions in the task_lifecycle
    """
    def setUp(self):  # noqa
        super(BasicTaskLifeCycleTestCase, self).setUp()
        setup_models(self)

    def test_worker_certified_for_task(self):
        task = Task.objects.filter(status=Task.Status.AWAITING_PROCESSING)[0]

        # workers[0] has a certification
        self.assertTrue(
            _worker_certified_for_task(self.workers[0],
                                       task,
                                       WorkerCertification.Role.ENTRY_LEVEL))

        # workers[2] has no certification
        self.assertFalse(
            _worker_certified_for_task(self.workers[2],
                                       task,
                                       WorkerCertification.Role.ENTRY_LEVEL))

    def test_check_worker_allowed_new_assignment(self):
        invalid_statuses = [Task.Status.PROCESSING,
                            Task.Status.REVIEWING,
                            Task.Status.POST_REVIEW_PROCESSING,
                            Task.Status.COMPLETE,
                            Task.Status.ABORTED]
        for status in invalid_statuses:
            with self.assertRaises(TaskStatusError):
                _check_worker_allowed_new_assignment(self.workers[2], status)

    def test_get_new_task_assignment_entry_level(self):
        # Entry-level assignment
        self.assertEquals(Task.objects
                          .filter(status=Task.Status.AWAITING_PROCESSING)
                          .count(),
                          1)

        with self.assertRaises(WorkerCertificationError):
            get_new_task_assignment(self.workers[5],
                                    Task.Status.PENDING_REVIEW)

        # assign a new task to a worker
        assignment = get_new_task_assignment(self.workers[5],
                                             Task.Status.AWAITING_PROCESSING)
        self.assertTrue(assignment is not None)

        self.assertEquals(assignment.task.status,
                          Task.Status.PROCESSING)

        # No more tasks left in AWAITING_PROCESSING
        with self.assertRaises(NoTaskAvailable):
            get_new_task_assignment(self.workers[5],
                                    Task.Status.AWAITING_PROCESSING)

        # Worker should not be served machine tasks
        workflow_slug = 'test_workflow_2'
        workflow = get_workflow_by_slug(workflow_slug)
        simple_machine = workflow.get_step('simple_machine')
        simple_machine.creation_depends_on = []

        project = Project.objects.create(workflow_slug=workflow_slug,
                                         short_description='',
                                         priority=0,
                                         task_class=0)
        Task.objects.create(project=project,
                            status=Task.Status.AWAITING_PROCESSING,
                            step_slug='simple_machine')

        with self.assertRaises(NoTaskAvailable):
            get_new_task_assignment(self.workers[5],
                                    Task.Status.AWAITING_PROCESSING)

    def test_get_new_task_assignment_reviewer(self):
        # Reviewer assignment
        self.assertEquals(Task.objects
                          .filter(status=Task.Status.PENDING_REVIEW)
                          .count(),
                          1)

        # assign a review task to worker
        assignment = get_new_task_assignment(self.workers[7],
                                             Task.Status.PENDING_REVIEW)
        self.assertTrue(assignment is not None)
        self.assertEquals(assignment.task.status,
                          Task.Status.REVIEWING)

        self.assertEquals(assignment.in_progress_task_data,
                          {'test_key': 'test_value'})

        # No tasks in state PENDING_REVIEW
        # No more tasks left in AWAITING_PROCESSING
        with self.assertRaises(NoTaskAvailable):
            get_new_task_assignment(self.workers[7],
                                    Task.Status.PENDING_REVIEW)

        # Assign an entry-level task to reviewer
        assignment = get_new_task_assignment(self.workers[7],
                                             Task.Status.AWAITING_PROCESSING)
        with self.assertRaises(NoTaskAvailable):
            get_new_task_assignment(self.workers[7],
                                    Task.Status.AWAITING_PROCESSING)

    def test_is_worker_assigned_to_task(self):
        task = self.tasks['review_task']

        # worker is not related to any task
        self.assertFalse(is_worker_assigned_to_task(self.workers[2],
                                                    task))

        # worker is assigned to a task.
        self.assertTrue(is_worker_assigned_to_task(self.workers[0],
                                                   task))

    # TODO(jrbotros): write this test when per-user max tasks logic created
    def test_worker_assigned_to_max_tasks(self):
        pass

    def test_worker_assigned_to_rejected_task(self):
        assignments = TaskAssignment.objects.filter(
            worker=self.workers[4],
            status=TaskAssignment.Status.PROCESSING,
            task__status=Task.Status.POST_REVIEW_PROCESSING)
        self.assertTrue(assignments.exists())
        self.assertTrue(worker_assigned_to_rejected_task(self.workers[4]))
        with self.assertRaises(TaskAssignmentError):
            get_new_task_assignment(self.workers[4],
                                    Task.Status.AWAITING_PROCESSING)

    def test_worker_has_reviewer_status(self):
        self.assertFalse(worker_has_reviewer_status(self.workers[0]))
        self.assertTrue(worker_has_reviewer_status(self.workers[1]))
        self.assertFalse(worker_has_reviewer_status(self.workers[2]))
        self.assertFalse(worker_has_reviewer_status(self.workers[4]))
        self.assertTrue(worker_has_reviewer_status(self.workers[5]))
        self.assertTrue(worker_has_reviewer_status(self.workers[6]))

    def test_assign_task(self):
        # Assign entry-level task to entry-level worker
        entry_tasks = Task.objects.filter(
            status=Task.Status.AWAITING_PROCESSING)
        self.assertEquals(entry_tasks.count(), 1)
        entry_task = entry_tasks.first()
        entry_task = assign_task(self.workers[0].id, entry_task.id)
        self.assertTrue(is_worker_assigned_to_task(self.workers[0],
                                                   entry_task))
        self.assertEquals(entry_task.status, Task.Status.PROCESSING)
        self.assertEquals(entry_task.assignments.count(), 1)

        # Attempt to reassign task to same worker
        with self.assertRaises(TaskAssignmentError):
            entry_task = assign_task(self.workers[0].id, entry_task.id)
        self.assertTrue(is_worker_assigned_to_task(self.workers[0],
                                                   entry_task))
        self.assertEquals(entry_task.status, Task.Status.PROCESSING)
        self.assertEquals(entry_task.assignments.count(), 1)

        # Reassign entry-level task to another entry-level worker
        entry_task = assign_task(self.workers[1].id, entry_task.id)
        self.assertFalse(is_worker_assigned_to_task(self.workers[0],
                                                    entry_task))
        self.assertTrue(is_worker_assigned_to_task(self.workers[1],
                                                   entry_task))
        self.assertEquals(entry_task.assignments.count(), 1)
        self.assertEquals(entry_task.status, Task.Status.PROCESSING)

        # Assign review task to review worker
        review_tasks = Task.objects.filter(status=Task.Status.PENDING_REVIEW)
        self.assertEquals(review_tasks.count(), 1)
        review_task = review_tasks.first()
        self.assertEquals(review_task.assignments.count(), 1)
        review_task = assign_task(self.workers[1].id, review_task.id)
        self.assertEquals(review_task.assignments.count(), 2)
        self.assertEqual(current_assignment(review_task).worker,
                         self.workers[1])
        self.assertEquals(review_task.status, Task.Status.REVIEWING)

        # Attempt to reassign review task to entry-level worker
        with self.assertRaises(WorkerCertificationError):
            review_task = assign_task(self.workers[0].id, review_task.id)
        self.assertEquals(review_task.assignments.count(), 2)
        self.assertEqual(current_assignment(review_task).worker,
                         self.workers[1])
        self.assertEquals(review_task.status, Task.Status.REVIEWING)

        # Reassign review task to another reviewer
        review_task = assign_task(self.workers[3].id, review_task.id)
        self.assertEquals(review_task.assignments.count(), 2)
        self.assertEqual(current_assignment(review_task).worker,
                         self.workers[3])
        self.assertEquals(review_task.status, Task.Status.REVIEWING)

        # Reassign rejected entry-level task to another entry-level worker
        reject_entry_tasks = Task.objects.filter(
            status=Task.Status.POST_REVIEW_PROCESSING,
            project=self.projects['reject_entry_proj'])
        self.assertEquals(reject_entry_tasks.count(), 1)
        reject_entry_task = reject_entry_tasks.first()
        reject_entry_task = assign_task(self.workers[5].id,
                                        reject_entry_task.id)
        self.assertFalse(is_worker_assigned_to_task(self.workers[4],
                                                    reject_entry_task))
        self.assertTrue(is_worker_assigned_to_task(self.workers[5],
                                                   reject_entry_task))
        self.assertEquals(reject_entry_task.status,
                          Task.Status.POST_REVIEW_PROCESSING)
        self.assertEquals(reject_entry_task.assignments.count(), 2)
        # In-progress data preserved after successful reassign
        self.assertEquals((current_assignment(reject_entry_task)
                           .in_progress_task_data),
                          {'test_key': 'test_value'})

        # Attempt to reassign rejected review task to entry-level worker
        reject_tasks = Task.objects.filter(
            status=Task.Status.POST_REVIEW_PROCESSING,
            project=self.projects['reject_rev_proj'])
        self.assertEquals(reject_tasks.count(), 1)
        reject_review_task = reject_tasks.first()
        with self.assertRaises(WorkerCertificationError):
            reject_review_task = assign_task(self.workers[4].id,
                                             reject_review_task.id)
        self.assertFalse(is_worker_assigned_to_task(self.workers[4],
                                                    reject_review_task))
        self.assertTrue(is_worker_assigned_to_task(self.workers[6],
                                                   reject_review_task))
        self.assertEquals(reject_review_task.status,
                          Task.Status.POST_REVIEW_PROCESSING)
        self.assertEquals(reject_review_task.assignments.count(), 3)

        # Reassign reviewer post-review task to another reviewer
        reject_review_task = assign_task(self.workers[8].id,
                                         reject_review_task.id)
        self.assertFalse(is_worker_assigned_to_task(self.workers[6],
                                                    reject_review_task))
        self.assertTrue(is_worker_assigned_to_task(self.workers[8],
                                                   reject_review_task))
        self.assertEquals(reject_review_task.status,
                          Task.Status.POST_REVIEW_PROCESSING)
        self.assertEquals(reject_review_task.assignments.count(), 3)

        # Attempt to reassign aborted task
        aborted_tasks = Task.objects.filter(status=Task.Status.ABORTED)
        self.assertEquals(aborted_tasks.count(), 1)
        aborted_task = aborted_tasks.first()
        with self.assertRaises(TaskStatusError):
            aborted_task = assign_task(self.workers[5].id, aborted_task.id)
        self.assertEquals(aborted_task.assignments.count(), 1)
        self.assertEqual(current_assignment(aborted_task).worker,
                         self.workers[4])

    def test_end_project(self):
        project = self.projects['project_to_end']
        end_project(project.id)
        self.assertEquals(Project.objects.get(id=project.id).status,
                          Project.Status.ABORTED)
        for task in Task.objects.filter(project=project):
            self.assertEquals(task.status, Task.Status.ABORTED)

    def test_get_task_overview_for_worker(self):
        task = self.tasks['review_task']

        with self.assertRaises(TaskAssignmentError):
            get_task_overview_for_worker(task.id, self.workers[2])

        data = get_task_overview_for_worker(task.id, self.workers[0])
        expected = {'project': {'details': task.project.short_description,
                                'id': task.project.id,
                                'project_data': {},
                                'review_document_url': None},
                    'workflow': {'slug': 'test_workflow',
                                 'name': 'The workflow'},
                    'prerequisites': {},
                    'step': {'slug': 'step1', 'name': 'The first step'},
                    'status': 'Submitted',
                    'task': {'data': {'test_key': 'test_value'},
                             'status': 'Pending Review'},
                    'task_id': task.id,
                    'is_reviewer': False,
                    'is_read_only': True,
                    'work_times_seconds': []}
        self.assertEquals(data,
                          expected)

    def test_task_assignment_saving(self):
        """
        Ensure that workers are required for human tasks,
        and no workers are required for machine tasks.
        """
        workflow_slug = 'test_workflow_2'
        workflow = get_workflow_by_slug(workflow_slug)
        simple_machine = workflow.get_step('simple_machine')
        simple_machine.creation_depends_on = []

        project = Project.objects.create(workflow_slug=workflow_slug,
                                         short_description='',
                                         priority=0,
                                         task_class=0)
        task = Task.objects.create(project=project,
                                   status=Task.Status.PROCESSING,
                                   step_slug='simple_machine')

        # We expect an error because a worker
        # is being saved on a machine task.
        with self.assertRaises(ModelSaveError):
            TaskAssignment.objects.create(worker=self.workers[0],
                                          task=task,
                                          status=0,
                                          in_progress_task_data={},
                                          snapshots={})

        task = Task.objects.create(project=project,
                                   status=Task.Status.PROCESSING,
                                   step_slug='step4')

        # We expect an error because no worker
        # is being saved on a human task
        with self.assertRaises(ModelSaveError):
            TaskAssignment.objects.create(task=task,
                                          status=0,
                                          in_progress_task_data={},
                                          snapshots={})

    def test_illegal_get_next_task_status(self):
        task = self.tasks['processing_task']
        illegal_statuses = [Task.Status.AWAITING_PROCESSING,
                            Task.Status.PENDING_REVIEW,
                            Task.Status.COMPLETE]

        snapshot_types = [TaskAssignment.SnapshotType.SUBMIT,
                          TaskAssignment.SnapshotType.ACCEPT,
                          TaskAssignment.SnapshotType.REJECT]

        for status in illegal_statuses:
            for snapshot_type in snapshot_types:
                with self.assertRaises(IllegalTaskSubmission):
                    task.status = Task.Status.REVIEWING
                    get_next_task_status(task,
                                         TaskAssignment.SnapshotType.SUBMIT)

        # Entry level-related statuses cannot be accepted or rejected
        with self.assertRaises(IllegalTaskSubmission):
            task.status = Task.Status.PROCESSING
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.ACCEPT)

        with self.assertRaises(IllegalTaskSubmission):
            task.status = Task.Status.PROCESSING
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.REJECT)

        with self.assertRaises(IllegalTaskSubmission):
            task.status = Task.Status.PROCESSING
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.ACCEPT)

        with self.assertRaises(IllegalTaskSubmission):
            task.status = Task.Status.POST_REVIEW_PROCESSING
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.REJECT)

        # Reviewer related statuses cannot be submitted
        with self.assertRaises(IllegalTaskSubmission):
            task.status = Task.Status.REVIEWING
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.SUBMIT)

    def test_sampled_get_next_task_status(self):
        task = self.tasks['processing_task']
        workflow = get_workflow_by_slug(task.project.workflow_slug)
        step = workflow.get_step(task.step_slug)
        step.review_policy = {'policy': 'sampled_review',
                              'rate': 0.5,
                              'max_reviews': 1}
        task.status = Task.Status.PROCESSING
        complete_count = 0
        for i in range(0, 1000):
            next_status = get_next_task_status(
                task, TaskAssignment.SnapshotType.SUBMIT)
            complete_count += next_status == Task.Status.COMPLETE
        self.assertTrue(complete_count > 400)
        self.assertTrue(complete_count < 600)

    def test_legal_get_next_task_status(self):
        task = self.tasks['processing_task']
        workflow = get_workflow_by_slug(task.project.workflow_slug)
        step = workflow.get_step(task.step_slug)
        step.review_policy = {}

        task.status = Task.Status.PROCESSING
        with self.assertRaises(ReviewPolicyError):
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.SUBMIT)

        step.review_policy = {'policy': 'sampled_review',
                              'rate': 1,
                              'max_reviews': 1}
        self.assertEquals(
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.SUBMIT),
            Task.Status.PENDING_REVIEW)

        step.review_policy = {'policy': 'sampled_review',
                              'rate': 0,
                              'max_reviews': 1}
        self.assertEquals(
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.SUBMIT),
            Task.Status.COMPLETE)

        task.status = Task.Status.POST_REVIEW_PROCESSING
        self.assertEquals(
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.SUBMIT),
            Task.Status.REVIEWING)

        task = self.tasks['review_task']
        task.status = Task.Status.REVIEWING

        step.review_policy = {'policy': 'sampled_review',
                              'rate': 1,
                              'max_reviews': 0}
        self.assertEquals(
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.ACCEPT),
            Task.Status.COMPLETE)

        step.review_policy = {'policy': 'sampled_review',
                              'rate': 1,
                              'max_reviews': 2}
        self.assertEquals(
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.ACCEPT),
            Task.Status.PENDING_REVIEW)

        # after max reviews done a task goes to state complete
        TaskAssignment.objects.create(worker=self.workers[1],
                                      task=task,
                                      status=TaskAssignment.Status.SUBMITTED,
                                      assignment_counter=1,
                                      in_progress_task_data={},
                                      snapshots=empty_snapshots())
        task.save()
        step.review_policy = {'policy': 'sampled_review',
                              'rate': 1,
                              'max_reviews': 1}
        self.assertEquals(
            get_next_task_status(task,
                                 TaskAssignment.SnapshotType.ACCEPT),
            Task.Status.COMPLETE)

    def test_task_history_details(self):
        task = self.tasks['processing_task']
        observed = task_history_details(task.id)
        observed['assignment_history'] = list(observed['assignment_history'])
        expected = {
            'current_assignment': current_assignment(task),
            'assignment_history': list(assignment_history(task))
        }
        self.assertEquals(
            json.dumps(observed, sort_keys=True),
            json.dumps(expected, sort_keys=True))

    def test_preassign_workers(self):
        project = self.projects['assignment_policy']

        # Create first task in test project
        create_subsequent_tasks(project)
        self.assertEquals(project.tasks.count(), 1)
        # Assign initial task to worker 0
        initial_task = assign_task(self.workers[0].id,
                                   project.tasks.first().id)
        # Submit task; next task should be created
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            initial_task = submit_task(initial_task.id, {},
                                       TaskAssignment.SnapshotType.SUBMIT,
                                       self.workers[0], 0)
        self.assertEquals(project.tasks.count(), 2)
        related_task = project.tasks.exclude(id=initial_task.id).first()
        # Worker 0 not certified for related tasks, so should not have been
        # auto-assigned
        self.assertEquals(related_task.assignments.count(), 0)
        self.assertEquals(related_task.status, Task.Status.AWAITING_PROCESSING)

        # Reset project
        project.tasks.all().delete()

        # Create first task in test project
        create_subsequent_tasks(project)
        self.assertEquals(project.tasks.count(), 1)
        # Assign initial task to worker 4
        initial_task = assign_task(self.workers[4].id,
                                   project.tasks.first().id)
        # Submit task; next task should be created
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            initial_task = submit_task(initial_task.id, {},
                                       TaskAssignment.SnapshotType.SUBMIT,
                                       self.workers[4], 0)
        self.assertEquals(project.tasks.count(), 2)
        related_task = project.tasks.exclude(id=initial_task.id).first()
        # Worker 4 is certified for related task and should have been assigned
        self.assertEquals(related_task.assignments.count(), 1)
        self.assertEquals(related_task.status, Task.Status.PROCESSING)
        self.assertTrue(is_worker_assigned_to_task(self.workers[4],
                                                   related_task))

        # Reset project
        project.tasks.all().delete()

    def test_malformed_assignment_policy(self):
        project = self.projects['assignment_policy']

        # Machine should not have an assignment policy
        workflow = get_workflow_by_slug('assignment_policy_workflow')
        machine_step = Step(
            slug='machine_step',
            worker_type=Step.WorkerType.MACHINE,
            assignment_policy={'policy': 'previously_completed_steps',
                               'steps': ['step_0']},
            creation_depends_on=[workflow.get_step('step_0')],
            function=lambda *args: None,
        )
        workflow.add_step(machine_step)

        # Create first task in project
        create_subsequent_tasks(project)
        self.assertEquals(project.tasks.count(), 1)

        # Assign initial task to worker 0 and mark as complete
        initial_task = assign_task(self.workers[4].id,
                                   project.tasks.first().id)
        initial_task.status = Task.Status.COMPLETE
        initial_task.save()

        # Cannot preassign machine task
        with self.assertRaises(AssignmentPolicyError):
            create_subsequent_tasks(project)

        # Reset project
        project.tasks.all().delete()

        # Machine should not be member of assignment policy
        (workflow.get_step('step_0')
            .assignment_policy) = {'policy': 'previously_completed_steps',
                                   'steps': ['machine_step']}
        with self.assertRaises(AssignmentPolicyError):
            create_subsequent_tasks(project)

        # Reset workflow and project
        (workflow.get_step('step_0')
            .assignment_policy) = {'policy': 'anyone_certified'}
        del workflow.steps['machine_step']
        project.tasks.all().delete()
