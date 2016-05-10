from unittest.mock import patch
from unittest.mock import MagicMock

from orchestra.core.errors import IllegalTaskSubmission
from orchestra.core.errors import NoTaskAvailable
from orchestra.core.errors import AssignmentPolicyError
from orchestra.core.errors import ModelSaveError
from orchestra.core.errors import ReviewPolicyError
from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import WorkerCertificationError
from orchestra.models import Iteration
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import WorkerCertification
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import StepFactory
from orchestra.tests.helpers.fixtures import TaskAssignmentFactory
from orchestra.tests.helpers.fixtures import TaskFactory
from orchestra.utils.task_lifecycle import AssignmentPolicyType
from orchestra.utils.task_lifecycle import is_worker_certified_for_task
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import get_new_task_assignment
from orchestra.utils.task_lifecycle import get_next_task_status
from orchestra.utils.task_lifecycle import get_task_overview_for_worker
from orchestra.utils.task_lifecycle import role_counter_required_for_new_task
from orchestra.utils.task_lifecycle import submit_task
from orchestra.utils.task_lifecycle import worker_assigned_to_rejected_task
from orchestra.utils.task_lifecycle import worker_has_reviewer_status
from orchestra.utils.task_properties import current_assignment


class BasicTaskLifeCycleTestCase(OrchestraTestCase):
    """
    Test modular functions in the task_lifecycle
    """

    def setUp(self):  # noqa
        super().setUp()
        setup_models(self)

    def test_is_worker_certified_for_task(self):
        task = Task.objects.filter(status=Task.Status.AWAITING_PROCESSING)[0]

        # workers[0] has a certification
        self.assertTrue(
            is_worker_certified_for_task(self.workers[0],
                                         task,
                                         WorkerCertification.Role.ENTRY_LEVEL))

        # workers[2] has no certification
        self.assertFalse(
            is_worker_certified_for_task(self.workers[2],
                                         task,
                                         WorkerCertification.Role.ENTRY_LEVEL))

    def test_not_allowed_new_assignment(self):
        invalid_statuses = [Task.Status.PROCESSING,
                            Task.Status.REVIEWING,
                            Task.Status.POST_REVIEW_PROCESSING,
                            Task.Status.COMPLETE,
                            Task.Status.ABORTED]
        for status in invalid_statuses:
            with self.assertRaises(TaskStatusError):
                get_new_task_assignment(self.workers[2], status)

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
        workflow_version = self.workflow_versions['test_workflow_2']
        simple_machine = self.workflow_steps[
            workflow_version.slug]['simple_machine']
        project = Project.objects.create(workflow_version=workflow_version,
                                         short_description='',
                                         priority=0,
                                         task_class=0)
        Task.objects.create(project=project,
                            status=Task.Status.AWAITING_PROCESSING,
                            step=simple_machine)

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

    def test_is_worker_assigned(self):
        task = self.tasks['review_task']

        # worker is not related to any task
        self.assertFalse(task.is_worker_assigned(self.workers[2]))

        # worker is assigned to a task.
        self.assertTrue(task.is_worker_assigned(self.workers[0]))

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

    def test_role_counter_required_for_new_task(self):
        task = TaskFactory(status=Task.Status.COMPLETE)
        with self.assertRaises(TaskAssignmentError):
            role_counter_required_for_new_task(task)

        project = self.projects['assignment_policy']

        # Create first task in test project
        create_subsequent_tasks(project)
        self.assertEquals(project.tasks.count(), 1)
        # Assign initial task to worker 0
        task = project.tasks.first()
        counter = role_counter_required_for_new_task(task)
        self.assertEquals(counter, 0)

        initial_task = assign_task(self.workers[0].id,
                                   task.id)
        # Submit task; next task should be created
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=True):
            initial_task = submit_task(initial_task.id, {},
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[0])

            counter = role_counter_required_for_new_task(initial_task)
            self.assertEquals(counter, 1)

            initial_task = assign_task(self.workers[1].id,
                                       task.id)
            initial_task = submit_task(initial_task.id, {},
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[1])
            counter = role_counter_required_for_new_task(initial_task)
            self.assertEquals(counter, 2)

    def test_assign_task(self):
        entry_task = TaskFactory(
            project=self.projects['base_test_project'],
            status=Task.Status.AWAITING_PROCESSING,
            step=self.test_step)

        # No iterations should be present for task
        self.assertEqual(
            Iteration.objects.filter(assignment__task=entry_task).count(), 0)

        # Assign entry-level task to entry-level worker
        entry_task = assign_task(self.workers[0].id, entry_task.id)
        self.assertTrue(entry_task.is_worker_assigned(self.workers[0]))
        self.assertEqual(entry_task.status, Task.Status.PROCESSING)

        self.assertEqual(entry_task.assignments.count(), 1)
        entry_assignment = entry_task.assignments.first()

        # A single iteration was created for the assignment
        self.assertEqual(entry_assignment.iterations.count(), 1)
        self.assertEqual(
            Iteration.objects.filter(assignment__task=entry_task).count(), 1)
        self.assertEqual(
            entry_assignment.iterations.first().start_datetime,
            entry_assignment.start_datetime)

        # Attempt to assign task which isn't awaiting a new assignment
        invalid = (Task.Status.PROCESSING, Task.Status.ABORTED,
                   Task.Status.REVIEWING, Task.Status.COMPLETE,
                   Task.Status.POST_REVIEW_PROCESSING)
        for status in invalid:
            invalid_status_task = Task.objects.create(
                project=self.projects['base_test_project'],
                status=status,
                step=self.test_step)

            with self.assertRaises(TaskAssignmentError):
                invalid_status_task = assign_task(
                    self.workers[0].id, invalid_status_task.id)

        # Attempt to assign review task to worker already in review hierarchy
        review_task = Task.objects.create(
            project=self.projects['base_test_project'],
            status=Task.Status.PENDING_REVIEW,
            step=self.test_step)
        test_data = {'test_assign': True}
        TaskAssignmentFactory(
            worker=self.workers[1],
            task=review_task,
            status=TaskAssignment.Status.SUBMITTED,
            in_progress_task_data=test_data)

        with self.assertRaises(TaskAssignmentError):
            assign_task(self.workers[1].id, review_task.id)
        self.assertEqual(
            current_assignment(review_task).in_progress_task_data, test_data)

        # Attempt to assign review task to worker not certified for task
        with self.assertRaises(WorkerCertificationError):
            assign_task(self.workers[2].id, review_task.id)
        self.assertEqual(
            current_assignment(review_task).in_progress_task_data, test_data)

        # Assign review task to review worker
        self.assertEquals(review_task.assignments.count(), 1)
        review_task = assign_task(self.workers[3].id, review_task.id)
        self.assertEquals(review_task.assignments.count(), 2)

        reviewer_assignment = current_assignment(review_task)
        self.assertEqual(
            reviewer_assignment.worker, self.workers[3])
        self.assertEqual(
            reviewer_assignment.in_progress_task_data, test_data)
        self.assertEquals(
            reviewer_assignment.iterations.count(), 1)
        self.assertEqual(
            reviewer_assignment.iterations.first().start_datetime,
            reviewer_assignment.start_datetime)

        self.assertEquals(
            review_task.status, Task.Status.REVIEWING)

    def test_get_task_overview_for_worker(self):
        task = self.tasks['review_task']

        with self.assertRaises(TaskAssignmentError):
            get_task_overview_for_worker(task.id, self.workers[2])

        data = get_task_overview_for_worker(task.id, self.workers[0])
        expected = {
            'project': {'details': task.project.short_description,
                        'id': task.project.id,
                        'project_data': {},
                        'team_messages_url': None},
            'workflow': {'slug': 'w1',
                         'name': 'Workflow One'},
            'workflow_version': {'slug': 'test_workflow',
                                 'name': 'The workflow'},
            'prerequisites': {},
            'step': {'slug': 'step1', 'name': 'The first step'},
            'status': 'Submitted',
            'task': {'data': {'test_key': 'test_value'},
                     'status': 'Pending Review'},
            'task_id': task.id,
            'assignment_id': task.assignments.get(worker=self.workers[0]).id,
            'is_reviewer': False,
            'is_read_only': True,
            'worker': {
                'username': self.workers[0].user.username,
                'first_name': self.workers[0].user.first_name,
                'last_name': self.workers[0].user.last_name,
            }
        }
        self.assertEquals(data, expected)

    def test_task_assignment_saving(self):
        """
        Ensure that workers are required for human tasks,
        and no workers are required for machine tasks.
        """
        workflow_version = self.workflow_versions['test_workflow_2']
        simple_machine = self.workflow_steps[
            workflow_version.slug]['simple_machine']
        project = Project.objects.create(workflow_version=workflow_version,
                                         short_description='',
                                         priority=0,
                                         task_class=0)
        task = Task.objects.create(project=project,
                                   status=Task.Status.PROCESSING,
                                   step=simple_machine)

        # We expect an error because a worker
        # is being saved on a machine task.
        with self.assertRaises(ModelSaveError):
            TaskAssignment.objects.create(worker=self.workers[0],
                                          task=task,
                                          status=0,
                                          in_progress_task_data={})

        human_step = self.workflow_steps[workflow_version.slug]['step4']
        task = Task.objects.create(project=project,
                                   status=Task.Status.PROCESSING,
                                   step=human_step)

        # We expect an error because no worker
        # is being saved on a human task
        with self.assertRaises(ModelSaveError):
            TaskAssignment.objects.create(task=task,
                                          status=0,
                                          in_progress_task_data={})

    def test_illegal_get_next_task_status(self):
        task = self.tasks['awaiting_processing']
        illegal_statuses = [
            Task.Status.AWAITING_PROCESSING,
            Task.Status.PENDING_REVIEW,
            Task.Status.COMPLETE
        ]

        iteration_statuses = [
            Iteration.Status.REQUESTED_REVIEW,
            Iteration.Status.PROVIDED_REVIEW
        ]

        for status in illegal_statuses:
            for iteration_status in iteration_statuses:
                with self.assertRaises(IllegalTaskSubmission):
                    task.status = status
                    get_next_task_status(task, iteration_status)

        # Entry level-related statuses cannot be rejected
        with self.assertRaises(IllegalTaskSubmission):
            task.status = Task.Status.PROCESSING
            get_next_task_status(task, Iteration.Status.PROVIDED_REVIEW)

        with self.assertRaises(IllegalTaskSubmission):
            task.status = Task.Status.POST_REVIEW_PROCESSING
            get_next_task_status(task, Iteration.Status.PROVIDED_REVIEW)

    def test_sampled_get_next_task_status(self):
        task = self.tasks['awaiting_processing']
        step = task.step
        step.review_policy = {'policy': 'sampled_review',
                              'rate': 0.5,
                              'max_reviews': 1}
        step.save()
        task.status = Task.Status.PROCESSING
        complete_count = 0
        for i in range(0, 1000):
            next_status = get_next_task_status(
                task, Iteration.Status.REQUESTED_REVIEW)
            complete_count += next_status == Task.Status.COMPLETE
        self.assertTrue(complete_count > 400)
        self.assertTrue(complete_count < 600)

    def test_legal_get_next_task_status(self):
        task = self.tasks['awaiting_processing']
        step = task.step

        task.status = Task.Status.PROCESSING
        step.review_policy = {}
        step.save()
        with self.assertRaises(ReviewPolicyError):
            get_next_task_status(task,
                                 Iteration.Status.REQUESTED_REVIEW)

        step.review_policy = {'policy': 'sampled_review',
                              'rate': 1,
                              'max_reviews': 1}
        step.save()
        self.assertEquals(
            get_next_task_status(task,
                                 Iteration.Status.REQUESTED_REVIEW),
            Task.Status.PENDING_REVIEW)

        step.review_policy = {'policy': 'sampled_review',
                              'rate': 0,
                              'max_reviews': 1}
        step.save()
        self.assertEquals(
            get_next_task_status(task,
                                 Iteration.Status.REQUESTED_REVIEW),
            Task.Status.COMPLETE)

        task.status = Task.Status.POST_REVIEW_PROCESSING
        self.assertEquals(
            get_next_task_status(task,
                                 Iteration.Status.REQUESTED_REVIEW),
            Task.Status.REVIEWING)

        task = self.tasks['review_task']
        task.status = Task.Status.REVIEWING

        step.review_policy = {'policy': 'sampled_review',
                              'rate': 1,
                              'max_reviews': 0}
        step.save()
        self.assertEquals(
            get_next_task_status(task,
                                 Iteration.Status.REQUESTED_REVIEW),
            Task.Status.COMPLETE)

        step.review_policy = {'policy': 'sampled_review',
                              'rate': 1,
                              'max_reviews': 2}
        step.save()
        self.assertEquals(
            get_next_task_status(task,
                                 Iteration.Status.REQUESTED_REVIEW),
            Task.Status.PENDING_REVIEW)

        # after max reviews done a task goes to state complete
        TaskAssignment.objects.create(
            worker=self.workers[1],
            task=task,
            status=TaskAssignment.Status.SUBMITTED,
            assignment_counter=1,
            in_progress_task_data={})
        task.save()
        step.review_policy = {'policy': 'sampled_review',
                              'rate': 1,
                              'max_reviews': 1}
        step.save()
        self.assertEquals(
            get_next_task_status(task,
                                 Iteration.Status.REQUESTED_REVIEW),
            Task.Status.COMPLETE)

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
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[0])
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
        # Assign initial task to worker 0
        initial_task = assign_task(self.workers[0].id,
                                   project.tasks.first().id)
        # Submit task; verify we use the reviewer assignment policy
        mock_preassign_workers = MagicMock(return_value=initial_task)
        patch_path = 'orchestra.utils.task_lifecycle._preassign_workers'
        with patch(patch_path, new=mock_preassign_workers):
            initial_task = submit_task(initial_task.id, {},
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[0])
            mock_preassign_workers.assert_called_once_with(
                initial_task, AssignmentPolicyType.REVIEWER)

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
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[4])
        self.assertEquals(project.tasks.count(), 2)
        related_task = project.tasks.exclude(id=initial_task.id).first()
        # Worker 4 is certified for related task and should have been assigned
        self.assertEquals(related_task.assignments.count(), 1)
        self.assertEquals(related_task.status, Task.Status.PROCESSING)
        self.assertTrue(
            related_task.is_worker_assigned(self.workers[4]))

        # Reset project
        project.tasks.all().delete()

    def test_malformed_assignment_policy(self):
        project = self.projects['assignment_policy']
        workflow_version = project.workflow_version
        first_step = self.workflow_steps[workflow_version.slug]['step_0']

        # Create an invalid machine step with an assignment policy
        malformed_step = StepFactory(
            workflow_version=workflow_version,
            slug='machine_step',
            is_human=False,
            assignment_policy={
                'policy_function': {
                    'entry_level': {
                        'path': ('orchestra.assignment_policies.'
                                 'previously_completed_steps'),
                        'kwargs': {
                            'related_steps': ['step_0']
                        },
                    }
                }
            },
        )
        malformed_step.creation_depends_on.add(first_step)

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
        first_step.assignment_policy = {
            'policy_function': {
                'entry_level': {
                    'path': ('orchestra.assignment_policies.'
                             'previously_completed_steps'),
                    'kwargs': {
                        'related_steps': ['machine_step']
                    },
                },
            }
        }
        first_step.save()
        with self.assertRaises(AssignmentPolicyError):
            create_subsequent_tasks(project)

        # Reset workflow and project
        first_step.assignment_policy = {}
        first_step.save()
        project.tasks.all().delete()
