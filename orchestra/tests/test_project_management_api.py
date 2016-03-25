import json
import time
from datetime import timedelta

from django.utils import timezone
from django.conf import settings
from django.contrib.auth.models import Group
from django.core.urlresolvers import reverse
from django.test import Client

from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Project
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_complete_task
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import UserFactory
from orchestra.tests.helpers.fixtures import WorkerFactory
from orchestra.utils.assignment_snapshots import empty_snapshots
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_properties import assignment_history
from orchestra.utils.task_properties import current_assignment


class ProjectManagementAPITestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)
        self.project_admin_group = Group.objects.create(name='project_admins')
        user = (UserFactory(username='project_management',
                            first_name='project_management',
                            last_name='project_management',
                            password='project_management',
                            email='project_management@unlimitedlabs.com'))
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
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))

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
        self.assertEquals(
            expected_project,
            {k: returned['project'][k] for k in expected_project.keys()})

        sample_task = returned['tasks']['step1']
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

        self.assertEquals(
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
            },
            'snapshots': empty_snapshots(),
            'iterations': [
                {
                    'start_datetime': '2015-10-12T01:00:00',
                    'end_datetime': '2015-10-12T02:00:00',
                }
            ],
            'in_progress_task_data': {},
            'id': assignment.id
        }

        self.assertEquals(
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
        self.assertEquals(response.status_code, 200)
        entry_assignment.refresh_from_db()
        self.assertEquals(entry_assignment.worker, self.workers[0])

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
        self.assertEquals(response.status_code, 200)
        entry_assignment.refresh_from_db()
        self.assertEquals(entry_assignment.worker, self.workers[1])

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
        self.assertEquals(response.status_code, 400)
        first_review_assignment.refresh_from_db()
        self.assertTrue(first_review_assignment.worker, self.workers[1])
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
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
        self.assertEquals(response.status_code, 400)
        first_review_assignment.refresh_from_db()
        self.assertTrue(first_review_assignment.worker, self.workers[0])
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
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
        self.assertEquals(response.status_code, 200)
        second_review_assignment.refresh_from_db()
        self.assertEquals(second_review_assignment.worker, self.workers[3])

    def test_revert_task_api(self):
        # Microseconds are truncated when manually saving models
        test_start = timezone.now().replace(microsecond=0)
        times = {
            'awaiting_pickup': test_start,
            'entry_pickup': test_start + timedelta(hours=1),
            'entry_submit': test_start + timedelta(hours=2),
            'reviewer_pickup': test_start + timedelta(hours=3),
            'reviewer_reject': test_start + timedelta(hours=4),
            'entry_resubmit': test_start + timedelta(hours=5),
            'reviewer_accept': test_start + timedelta(hours=6),
        }

        # Revert past end of task should have no effect
        self._test_reverted_task(
            times,
            datetime=times['reviewer_accept'] + timedelta(hours=0.5),
            status=Task.Status.COMPLETE,
            num_assignments=2,
            num_snapshots_per_assignment=[2, 2],
            latest_data={'test': 'reviewer_accept'})

        # Revert before reviewer acceptance but retain latest data
        self._test_reverted_task(
            times,
            datetime=times['reviewer_accept'],
            status=Task.Status.REVIEWING,
            num_assignments=2,
            num_snapshots_per_assignment=[2, 1],
            latest_data={'test': 'reviewer_accept'})
        self._test_reverted_task(
            times,
            datetime=times['reviewer_accept'] - timedelta(hours=0.5),
            status=Task.Status.REVIEWING,
            num_assignments=2,
            num_snapshots_per_assignment=[2, 1],
            latest_data={'test': 'reviewer_accept'})

        # Revert before entry resubmission but retain latest data
        self._test_reverted_task(
            times,
            datetime=times['entry_resubmit'],
            status=Task.Status.POST_REVIEW_PROCESSING,
            num_assignments=2,
            num_snapshots_per_assignment=[1, 1],
            latest_data={'test': 'entry_resubmit'})
        self._test_reverted_task(
            times,
            datetime=times['entry_resubmit'] - timedelta(hours=0.5),
            status=Task.Status.POST_REVIEW_PROCESSING,
            num_assignments=2,
            num_snapshots_per_assignment=[1, 1],
            latest_data={'test': 'entry_resubmit'})

        # Revert before reviewer rejection but retain latest data
        self._test_reverted_task(
            times,
            datetime=times['reviewer_reject'],
            status=Task.Status.REVIEWING,
            num_assignments=2,
            num_snapshots_per_assignment=[1, 0],
            latest_data={'test': 'reviewer_reject'})
        self._test_reverted_task(
            times,
            datetime=times['reviewer_reject'] - timedelta(hours=0.5),
            status=Task.Status.REVIEWING,
            num_assignments=2,
            num_snapshots_per_assignment=[1, 0],
            latest_data={'test': 'reviewer_reject'})

        # Revert before reviewer pickup but retain latest data
        self._test_reverted_task(
            times,
            datetime=times['reviewer_pickup'],
            status=Task.Status.PENDING_REVIEW,
            num_assignments=1,
            num_snapshots_per_assignment=[1],
            latest_data={'test': 'entry_submit'})
        self._test_reverted_task(
            times,
            datetime=times['reviewer_pickup'] - timedelta(hours=0.5),
            status=Task.Status.PENDING_REVIEW,
            num_assignments=1,
            num_snapshots_per_assignment=[1],
            latest_data={'test': 'entry_submit'})

        # Revert before entry submission but retain latest data
        self._test_reverted_task(
            times,
            datetime=times['entry_submit'],
            status=Task.Status.PROCESSING,
            num_assignments=1,
            num_snapshots_per_assignment=[0],
            latest_data={'test': 'entry_submit'})
        self._test_reverted_task(
            times,
            datetime=times['entry_submit'] - timedelta(hours=0.5),
            status=Task.Status.PROCESSING,
            num_assignments=1,
            num_snapshots_per_assignment=[0],
            latest_data={'test': 'entry_submit'})

        # Revert before entry submission but retain latest data
        self._test_reverted_task(
            times,
            datetime=times['entry_pickup'],
            status=Task.Status.AWAITING_PROCESSING,
            num_assignments=0,
            num_snapshots_per_assignment=[],
            latest_data={})
        self._test_reverted_task(
            times,
            datetime=times['entry_pickup'] - timedelta(hours=0.5),
            status=Task.Status.AWAITING_PROCESSING,
            num_assignments=0,
            num_snapshots_per_assignment=[],
            latest_data={})

        task = setup_complete_task(self, times)
        datetime = times['awaiting_pickup']
        response = self.api_client.post(
            reverse('orchestra:orchestra:project_management:revert_task'),
            json.dumps({
                'task_id': task.id,
                # Convert datetime to timestamp
                'revert_datetime': time.mktime(datetime.timetuple()),
                'fake': False
            }),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)
        with self.assertRaises(Task.DoesNotExist):
            Task.objects.get(id=task.id)

        task = setup_complete_task(self, times)
        datetime = times['awaiting_pickup'] - timedelta(hours=0.5)
        response = self.api_client.post(
            reverse('orchestra:orchestra:project_management:revert_task'),
            json.dumps({
                'task_id': task.id,
                # Convert datetime to timestamp
                'revert_datetime': time.mktime(datetime.timetuple()),
                'fake': False
            }),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)
        with self.assertRaises(Task.DoesNotExist):
            Task.objects.get(id=task.id)

    def test_complete_and_skip_task_api(self):
        task = self.tasks['project_management_task']
        response = self.api_client.post(
            reverse(
                'orchestra:orchestra:project_management:'
                'complete_and_skip_task'),
            json.dumps({
                'task_id': task.id,
            }),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)
        task.refresh_from_db()
        self.assertEquals(task.status, Task.Status.COMPLETE)
        for assignment in task.assignments.all():
            self.assertEquals(
                assignment.status, TaskAssignment.Status.SUBMITTED)

        # Check that dependent tasks have already been created
        # TODO(jrbotros): Create a `get_dependent_tasks` function
        num_tasks = task.project.tasks.count()
        create_subsequent_tasks(task.project)
        self.assertEquals(task.project.tasks.count(), num_tasks)

    def test_end_project_api(self):
        project = self.projects['project_to_end']
        response = self.api_client.post(
            reverse('orchestra:orchestra:project_management:end_project'),
            json.dumps({
                'project_id': project.id,
            }),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)
        project.refresh_from_db()
        self.assertEquals(project.status, Project.Status.ABORTED)
        for task in Task.objects.filter(project=project):
            self.assertEquals(task.status, Task.Status.ABORTED)

    def _test_audit(self, audit, num_assignments,
                    num_snapshots_per_assignment, deleted=False):
        if deleted:
            self.assertEquals(audit['change'], 'deleted')
        if num_assignments == 2 and num_snapshots_per_assignment == [2, 2]:
            self.assertEquals(audit['change'], 'unchanged')
        else:
            self.assertEquals(audit['change'], 'reverted')
        for i, assignment in enumerate(audit['assignments']):
            try:
                num_snapshots = num_snapshots_per_assignment[i]
            except IndexError:
                num_snapshots = 0
            if i > num_assignments - 1:
                assignment['change'] == 'deleted'
            if num_snapshots == 2:
                assignment['change'] == 'unchanged'
            else:
                assignment['change'] == 'reverted'
            for j, snapshot in enumerate(assignment['snapshots']):
                if j > num_snapshots - 1:
                    self.assertEquals(snapshot['change'], 'deleted')
                else:
                    self.assertEquals(snapshot['change'], 'unchanged')

    def _test_reverted_task(self, times, datetime, status, num_assignments,
                            num_snapshots_per_assignment, latest_data):
        task = setup_complete_task(self, times)
        response = self.api_client.post(
            reverse('orchestra:orchestra:project_management:revert_task'),
            json.dumps({
                'task_id': task.id,
                # Convert datetime to timestamp
                'revert_datetime': time.mktime(datetime.timetuple()),
                'fake': True
            }),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)
        task.refresh_from_db()
        self.assertEquals(task.status, Task.Status.COMPLETE)
        self.assertEquals(task.assignments.count(), 2)
        for assignment in task.assignments.all():
            self.assertEquals(
                len(assignment.snapshots['snapshots']), 2)

        response = self.api_client.post(
            reverse('orchestra:orchestra:project_management:revert_task'),
            json.dumps({
                'task_id': task.id,
                # Convert datetime to timestamp
                'revert_datetime': time.mktime(datetime.timetuple()),
                'fake': False
            }),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)
        audit = json.loads(response.content.decode('utf-8'))
        self._test_audit(audit, num_assignments, num_snapshots_per_assignment)

        task.refresh_from_db()
        self.assertEquals(task.status, status)

        assignments = assignment_history(task)
        self.assertEquals(task.assignments.count(), num_assignments)
        self.assertEquals(
            len(num_snapshots_per_assignment), num_assignments)
        for i, num_snapshots in enumerate(num_snapshots_per_assignment):
            self.assertEquals(
                len(assignments[i].snapshots['snapshots']), num_snapshots)

        if num_assignments:
            self.assertEquals(
                current_assignment(task).in_progress_task_data,
                latest_data)

        task.delete()
