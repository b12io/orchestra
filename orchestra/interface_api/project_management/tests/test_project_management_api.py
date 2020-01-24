import json
from unittest.mock import patch

from django.conf import settings
from django.contrib.auth.models import Group
from django.urls import reverse
from django.test import Client
from django.test import override_settings

from orchestra.core.errors import InvalidRevertError
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.project_api.serializers import IterationSerializer
from orchestra.project_api.serializers import TaskAssignmentSerializer
from orchestra.project_api.serializers import TaskSerializer
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.tests.helpers.fixtures import setup_complete_task
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.iterations import verify_iterations
from orchestra.utils.load_json import load_encoded_json
from orchestra.utils.revert import RevertChange
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import complete_and_skip_task
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import current_assignment
from orchestra.utils.task_properties import get_iteration_history
from orchestra.utils.task_properties import get_latest_iteration


class ProjectManagementAPITestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.project_admin_group = Group.objects.create(name='project_admins')
        user = (UserFactory(username='project_management',
                            first_name='project_management',
                            last_name='project_management',
                            password='project_management',
                            email='project_management@b12.io'))
        self.worker = WorkerFactory(user=user)
        user.groups.add(self.project_admin_group)

        self.api_client = Client()
        self.api_client.login(
            username='project_management', password='project_management')

    def test_project_information_api(self):
        project = self.projects['project_management_project']
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:'
                'project_information'),
            json.dumps({
                'project_id': project.id,
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        returned = load_encoded_json(response.content)

        # Skipping the `tasks` key/value pair for this test
        expected_project = {
            'task_class': project.task_class,
            'start_datetime': '2015-10-12T00:00:00Z',
            'team_messages_url': None,
            'admin_url': settings.ORCHESTRA_URL + reverse(
                'admin:orchestra_project_change',
                args=(project.id,)),
            'priority': project.priority,
            'project_data': project.project_data,
            'short_description': project.short_description,
            'id': project.id,
            'workflow_slug': project.workflow_version.workflow.slug
        }
        returned_project = returned[str(project.id)]['project']
        self.assertEqual(
            expected_project,
            {k: returned_project[k] for k in expected_project.keys()})

        sample_task = returned[str(project.id)]['tasks']['step1']
        task = project.tasks.get(step__slug='step1')
        expected_task = {
            'status': 'Post-review Processing',
            'start_datetime': '2015-10-12T01:00:00Z',
            'admin_url': settings.ORCHESTRA_URL + reverse(
                'admin:orchestra_task_change',
                args=(task.id,)),
            'latest_data': {
                'test_key': 'test_value'
            },
            'project': task.project.id,
            'step_slug': 'step1',
            'id': task.id
        }

        self.assertEqual(
            expected_task,
            {k: sample_task[k] for k in expected_task.keys()})

        sample_assignment = sample_task['assignments'][0]
        assignment = assignment_history(task)[0]
        expected_assignment = {
            'status': 'Submitted',
            'start_datetime': '2015-10-12T02:00:00Z',
            'task': assignment.task.id,
            'admin_url': settings.ORCHESTRA_URL + reverse(
                'admin:orchestra_taskassignment_change',
                args=(assignment.id,)),
            'worker': {
                'username': assignment.worker.user.username,
                'first_name': assignment.worker.user.first_name,
                'last_name': assignment.worker.user.last_name,
                'id': assignment.worker.id,
                'slack_username': assignment.worker.slack_username,
                'slack_user_id': assignment.worker.slack_user_id
            },
            'iterations': [
                {
                    'id': assignment.iterations.first().id,
                    'admin_url': settings.ORCHESTRA_URL + reverse(
                        'admin:orchestra_iteration_change',
                        args=(assignment.iterations.first().id,)),
                    'assignment': assignment.id,
                    'start_datetime': '2015-10-12T02:00:00Z',
                    'end_datetime': '2015-10-12T03:00:00Z',
                    'status': 'Requested Review',
                    'submitted_data': {}
                }
            ],
            'in_progress_task_data': {},
            'id': assignment.id
        }

        self.assertEqual(
            expected_assignment,
            {k: sample_assignment[k] for k in expected_assignment.keys()})

    def test_reassign_assignment_api(self):
        task = self.tasks['project_management_task']
        # Reassign entry-level assignment to entry-level worker
        entry_assignment = task.assignments.get(assignment_counter=0)
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:reassign_assignment'),
            json.dumps({
                'worker_username': self.workers[0].user.username,
                'assignment_id': entry_assignment.id
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        entry_assignment.refresh_from_db()
        self.assertEqual(entry_assignment.worker, self.workers[0])

        # Reassign entry-level assignment to reviewer
        entry_assignment.refresh_from_db()
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:reassign_assignment'),
            json.dumps({
                'worker_username': self.workers[1].user.username,
                'assignment_id': entry_assignment.id
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        entry_assignment.refresh_from_db()
        self.assertEqual(entry_assignment.worker, self.workers[1])

        # Attempt to reassign assignment to worker already working on task
        first_review_assignment = task.assignments.get(assignment_counter=1)
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:reassign_assignment'),
            json.dumps({
                'worker_username': self.workers[1].user.username,
                'assignment_id': first_review_assignment.id
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        first_review_assignment.refresh_from_db()
        self.assertTrue(first_review_assignment.worker, self.workers[1])
        returned = load_encoded_json(response.content)
        self.assertEqual(returned['message'],
                         'Worker already assigned to this task.')

        # Attempt to reassign review assignment to entry-level worker
        first_review_assignment = task.assignments.get(assignment_counter=1)
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:reassign_assignment'),
            json.dumps({
                'worker_username': self.workers[0].user.username,
                'assignment_id': first_review_assignment.id
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 400)
        first_review_assignment.refresh_from_db()
        self.assertTrue(first_review_assignment.worker, self.workers[0])
        returned = load_encoded_json(response.content)
        self.assertEqual(returned['message'],
                         'Worker not certified for this assignment.')

        # Reassign review assignment to another reviewer
        second_review_assignment = task.assignments.get(assignment_counter=2)
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:reassign_assignment'),
            json.dumps({
                'worker_username': self.workers[3].user.username,
                'assignment_id': second_review_assignment.id
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        second_review_assignment.refresh_from_db()
        self.assertEqual(second_review_assignment.worker, self.workers[3])

    def test_complete_and_skip_task_api(self):
        # This task, when submitted, will be moved into reviewing
        # state because it's already been assigned.
        task = self.tasks['project_management_task']
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:'
                'complete_and_skip_task'),
            json.dumps({
                'task_id': task.id,
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.REVIEWING)
        assignment_statuses = [
            TaskAssignment.Status.SUBMITTED, TaskAssignment.Status.SUBMITTED,
            TaskAssignment.Status.PROCESSING]
        for index, assignment in enumerate(
                task.assignments.all().order_by('assignment_counter')):
            self.assertEqual(
                assignment.status, assignment_statuses[index])
        # Check that dependent tasks have already been created
        num_tasks = task.project.tasks.count()
        create_subsequent_tasks(task.project)
        self.assertEqual(task.project.tasks.count(), num_tasks)

        # This task, when submitted, will be moved into a completed
        # state because it has no assignments.
        task = self.tasks['awaiting_processing']
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:'
                'complete_and_skip_task'),
            json.dumps({
                'task_id': task.id,
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        self.assertEqual(task.status, Task.Status.COMPLETE)

    @override_settings(ORCHESTRA_SLACK_EXPERTS_ENABLED=True)
    @patch('orchestra.communication.tests.helpers.slack.Groups.unarchive')
    @patch('orchestra.communication.tests.helpers.slack.Groups.archive')
    def test_unarchive_slack_channel_api(self, mock_archive, mock_unarchive):
        project = self.projects['single_human_step']
        create_subsequent_tasks(project)
        task = Task.objects.get(project=project)
        assign_task(self.workers[1].id, task.id)
        complete_and_skip_task(task.id)
        create_subsequent_tasks(project)
        self.assertTrue(mock_archive.called)

        response = self.api_client.post(
            reverse(('orchestra:orchestra:project_management'
                     ':unarchive_slack_channel')),
            json.dumps({
                'project_id': project.id,
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        self.assertTrue(mock_unarchive.called)

    def test_end_project_api(self):
        project = self.projects['project_to_end']
        response = self.api_client.post(
            reverse('orchestra:orchestra:project_management:end_project'),
            json.dumps({
                'project_id': project.id,
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.ABORTED)
        for task in Task.objects.filter(project=project):
            self.assertEqual(task.status, Task.Status.ABORTED)

    def test_set_project_status_api(self):
        project = self.projects['project_to_set_status']
        status_choices = dict(Project.STATUS_CHOICES)
        paused_status = status_choices[Project.Status.PAUSED]
        active_status = status_choices[Project.Status.ACTIVE]
        response = self.api_client.post(
            reverse((
                'orchestra:orchestra:project_management:'
                'set_project_status')),
            json.dumps({
                'project_id': project.id,
                'status': paused_status
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.PAUSED)

        response = self.api_client.post(
            reverse((
                'orchestra:orchestra:project_management:'
                'set_project_status')),
            json.dumps({
                'project_id': project.id,
                'status': active_status
            }),
            content_type='application/json')
        self.assertEqual(response.status_code, 200)
        project.refresh_from_db()
        self.assertEqual(project.status, Project.Status.ACTIVE)

    def test_invalid_revert_aborted_task(self):
        task = setup_complete_task(self)
        task.status = Task.Status.ABORTED
        task.save()

        with self.assertRaises(InvalidRevertError):
            self._revert_task(
                task, task.assignments.first().iterations.first(),
                revert_before=False, commit=True)

        task.delete()

    def test_invalid_revert_before(self):
        task = setup_complete_task(self)
        task.status = Task.Status.ABORTED
        task.save()

        # Ensure reviewer assignment has more than one iteration
        reviewer_assignment = assignment_history(task).last()
        self.assertGreater(reviewer_assignment.iterations.count(), 1)

        # Attempt to revert before an iteration that isn't the assignment's
        # first
        with self.assertRaises(InvalidRevertError):
            self._revert_task(
                task, get_latest_iteration(reviewer_assignment),
                revert_before=True, commit=True)

        task.delete()

    def test_revert_second_review(self):
        task = setup_complete_task(self)
        reverted_status = Task.Status.REVIEWING

        expected_audit = self._expected_audit(
            task,
            reverted_status=reverted_status,
            assignment_changes=(
                RevertChange.UNCHANGED.value, RevertChange.REVERTED.value),
            iteration_changes=(
                (RevertChange.UNCHANGED.value, RevertChange.UNCHANGED.value),
                (RevertChange.UNCHANGED.value, RevertChange.REVERTED.value)
            ))

        self._test_reverted_task(
            task,
            iteration=get_iteration_history(task).all()[3],
            num_iterations=4,
            task_status=reverted_status,
            latest_data={'test': 'reviewer_accept'},
            expected_audit=expected_audit)

        task.delete()

    def test_revert_post_review_processing(self):
        task = setup_complete_task(self)
        reverted_status = Task.Status.POST_REVIEW_PROCESSING

        expected_audit = self._expected_audit(
            task,
            reverted_status=reverted_status,
            assignment_changes=(
                RevertChange.REVERTED.value, RevertChange.REVERTED.value),
            iteration_changes=(
                (RevertChange.UNCHANGED.value, RevertChange.REVERTED.value),
                (RevertChange.UNCHANGED.value, RevertChange.DELETED.value)
            ))

        self._test_reverted_task(
            task,
            iteration=get_iteration_history(task).all()[2],
            num_iterations=3,
            task_status=reverted_status,
            latest_data={'test': 'entry_resubmit'},
            expected_audit=expected_audit)

        task.delete()

    def test_revert_first_review(self):
        task = setup_complete_task(self)
        reverted_status = Task.Status.REVIEWING

        expected_audit = self._expected_audit(
            task,
            reverted_status=reverted_status,
            assignment_changes=(
                RevertChange.REVERTED.value, RevertChange.REVERTED.value),
            iteration_changes=(
                (RevertChange.UNCHANGED.value, RevertChange.DELETED.value),
                (RevertChange.REVERTED.value, RevertChange.DELETED.value)
            ))

        self._test_reverted_task(
            task,
            iteration=get_iteration_history(task).all()[1],
            num_iterations=2,
            task_status=reverted_status,
            latest_data={'test': 'reviewer_accept'},
            expected_audit=expected_audit)

        task.delete()

    def test_revert_pending_review(self):
        task = setup_complete_task(self)
        reverted_status = Task.Status.PENDING_REVIEW

        expected_audit = self._expected_audit(
            task,
            reverted_status=reverted_status,
            assignment_changes=(
                RevertChange.REVERTED.value, RevertChange.DELETED.value),
            iteration_changes=(
                (RevertChange.UNCHANGED.value, RevertChange.DELETED.value),
                (RevertChange.DELETED.value, RevertChange.DELETED.value)
            ))

        self._test_reverted_task(
            task,
            iteration=get_iteration_history(task).all()[1],
            num_iterations=1,
            task_status=reverted_status,
            latest_data={'test': 'entry_resubmit'},
            expected_audit=expected_audit,
            revert_before=True)

        task.delete()

    def test_revert_processing(self):
        task = setup_complete_task(self)
        reverted_status = Task.Status.PROCESSING

        expected_audit = self._expected_audit(
            task,
            reverted_status=reverted_status,
            assignment_changes=(
                RevertChange.REVERTED.value, RevertChange.DELETED.value),
            iteration_changes=(
                (RevertChange.REVERTED.value, RevertChange.DELETED.value),
                (RevertChange.DELETED.value, RevertChange.DELETED.value)
            ))

        self._test_reverted_task(
            task,
            iteration=get_iteration_history(task).all()[0],
            num_iterations=1,
            task_status=reverted_status,
            latest_data={'test': 'entry_resubmit'},
            expected_audit=expected_audit)

        task.delete()

    def test_revert_awaiting_processing(self):
        task = setup_complete_task(self)
        reverted_status = Task.Status.AWAITING_PROCESSING

        expected_audit = self._expected_audit(
            task,
            reverted_status=reverted_status,
            assignment_changes=(
                RevertChange.DELETED.value, RevertChange.DELETED.value),
            iteration_changes=(
                (RevertChange.DELETED.value, RevertChange.DELETED.value),
                (RevertChange.DELETED.value, RevertChange.DELETED.value)
            ))

        self._test_reverted_task(
            task,
            iteration=get_iteration_history(task).all()[0],
            num_iterations=0,
            task_status=reverted_status,
            latest_data={'test': 'entry_resubmit'},
            expected_audit=expected_audit,
            revert_before=True)

        task.delete()

    def _revert_task(self, task, iteration, revert_before, commit):
        return self.api_client.post(
            reverse('orchestra:orchestra:project_management:revert_task'),
            json.dumps({
                'task_id': task.id,
                # Convert datetime to timestamp
                'iteration_id': iteration.id,
                'revert_before': revert_before,
                'commit': commit,
            }),
            content_type='application/json')

    def _test_reverted_task(self, task, iteration, num_iterations,
                            task_status, latest_data, expected_audit,
                            revert_before=False):
        response = self._revert_task(
            task, iteration, revert_before=revert_before, commit=False)
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        fake_audit = load_encoded_json(response.content)
        self.assertEqual(fake_audit, expected_audit)

        self.assertEqual(task.status, Task.Status.COMPLETE)
        self.assertEqual(task.assignments.count(), 2)
        for assignment in task.assignments.all():
            self.assertEqual(assignment.iterations.count(), 2)

        response = self._revert_task(
            task, iteration, revert_before=revert_before, commit=True)
        self.assertEqual(response.status_code, 200)
        task.refresh_from_db()
        audit = load_encoded_json(response.content)
        self.assertEqual(audit, fake_audit)
        task.refresh_from_db()
        self.assertEqual(task.status, task_status)
        self.assertEqual(
            get_iteration_history(task).count(), num_iterations)

        verify_iterations(task.id)

        if num_iterations:
            self.assertEqual(
                current_assignment(task).in_progress_task_data,
                latest_data)

        verify_iterations(task.id)

    def _expected_audit(self, complete_task, reverted_status=None,
                        assignment_changes=None, iteration_changes=None):
        assignments = assignment_history(complete_task)
        iterations = get_iteration_history(complete_task)
        audit = {
            'task': TaskSerializer(complete_task).data,
            'assignments': [
                {
                    'assignment': (
                        TaskAssignmentSerializer(assignments.first()).data),
                    'change': 0,
                    'iterations': [
                        {
                            'change': 0,
                            'iteration': (
                                IterationSerializer(iterations.all()[0]).data)
                        },
                        {
                            'change': 0,
                            'iteration': (
                                IterationSerializer(iterations.all()[2]).data)
                        }
                    ]
                },
                {
                    'assignment': (
                        TaskAssignmentSerializer(assignments.last()).data),
                    'change': 0,
                    'iterations': [
                        {
                            'change': 0,
                            'iteration': (
                                IterationSerializer(iterations.all()[1]).data)
                        },
                        {
                            'change': 0,
                            'iteration': (
                                IterationSerializer(iterations.all()[3]).data)
                        }
                    ]
                }
            ],
        }
        if reverted_status is not None:
            audit['reverted_status'] = reverted_status
        if assignment_changes is not None:
            for i, assignment_change in enumerate(assignment_changes):
                audit['assignments'][i]['change'] = assignment_change
        if iteration_changes is not None:
            for i, changes_per_assignment in enumerate(iteration_changes):
                for j, iteration_change in enumerate(changes_per_assignment):
                    audit['assignments'][i][
                        'iterations'][j]['change'] = iteration_change
        return audit

    @patch('orchestra.interface_api.project_management.views.StaffBot.restaff')
    @patch('orchestra.interface_api.project_management.views.StaffBot.staff')
    def test_staff_task(self, mock_staff, mock_restaff):
        # Staff a task with no assignment
        unassigned_task = self.tasks['awaiting_processing']
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:staff_task'),
            json.dumps({
                'task_id': unassigned_task.id
            }),
            content_type='application/json')
        self.assertTrue(mock_staff.called)
        self.assertEqual(response.status_code, 200)
        is_restaff = load_encoded_json(response.content)['is_restaff']
        self.assertFalse(is_restaff)

        # Restaff a task with an assignment
        assigned_task = self.tasks['review_task']
        response2 = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:staff_task'),
            json.dumps({
                'task_id': assigned_task.id
            }),
            content_type='application/json')
        self.assertTrue(mock_restaff.called)
        self.assertEqual(response2.status_code, 200)
        is_restaff2 = load_encoded_json(response2.content)['is_restaff']
        self.assertTrue(is_restaff2)
