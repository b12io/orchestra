import json

from copy import deepcopy
from datetime import datetime
from django.test import override_settings
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.workflow import get_workflow_by_slug
from orchestra.workflow import Step
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.assignment_snapshots import load_snapshots


class DashboardTestCase(OrchestraTestCase):
    def setUp(self):  # noqa
        super(DashboardTestCase, self).setUp()
        setup_models(self)

    @override_settings(MACHINE_STEP_SCHEDULER=(
        'orchestra.utils.machine_step_scheduler',
        'SynchronousMachineStepScheduler'))
    def test_task_creation(self):
        """
        Test human and machine task creation
        """
        Task.objects.filter(status=Task.Status.AWAITING_PROCESSING).delete()

        project = self.projects['test_human_and_machine']
        self.assertEquals(Task.objects.filter(project=project).count(),
                          0)
        create_subsequent_tasks(project)

        # Human Task was created
        self.assertEquals(Task.objects.filter(project=project).count(),
                          1)

        response = (self.clients[0].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))
        self.assertEquals(response.status_code, 200)

        task = Task.objects.get(step_slug='step4', project=project)
        data = {'submit_key1': 'submit_val1'}

        # user 0 submits a task
        response = self._submit_assignment(self.clients[0], task.id, data=data)
        self.assertEquals(response.status_code, 200)

        # Machine Task was created
        self.assertEquals(Task.objects.filter(project=project).count(),
                          2)
        machine_task_assignment = (
            TaskAssignment.objects
            .filter(task__step_slug='simple_machine',
                    task__project=project)[0])

        self.assertTrue(machine_task_assignment.status,
                        TaskAssignment.Status.SUBMITTED)

        self.assertTrue(machine_task_assignment.in_progress_task_data,
                        {'simple': 'json'})

        self.assertTrue(machine_task_assignment.task.status,
                        Task.Status.COMPLETE)

    def test_index(self):
        response = self.clients[0].get('/orchestra/app/')
        self.assertEquals(response.status_code, 200)

    def test_status(self):
        response = self.clients[0].get('/orchestra/status/')
        self.assertEquals(response.status_code, 200)

    def test_dashboard_tasks(self):
        self._check_client_dashboard_state(self.clients[0], 'pending_review')

    def test_entry_level_task_assignment(self):
        response = (self.clients[2].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))

        # no task available for user3 because no entry-level certification
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'No worker certificates')

        # user 0 only has certification for entry level tasks
        response = (self.clients[0].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))

        task_id = returned['id']
        task = Task.objects.get(id=task_id)
        self.assertEquals(
            {'id': task.id,
             'step': task.step_slug,
             'project': task.project.workflow_slug,
             'detail': task.project.short_description},
            returned)

        # task assignment for invalid id should give bad request
        self._verify_bad_task_assignment_information(
            self.clients[0], {'task_id': -1},
            'Task matching query does not exist.')

        # task assignment for user3 not assigned to a task
        self._verify_bad_task_assignment_information(
            self.clients[2], {'task_id': task_id},
            'Worker is not associated with task')

        # task assignment is assigned to user 0
        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task_id},
            task.project.short_description,
            'Processing', 'Processing', False,
            False, {})

        # no more tasks for user 0 left
        response = (self.clients[0].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'No task')

    def _check_client_dashboard_state(self, client, non_empty_status):
        response = client.get('/orchestra/api/interface/dashboard_tasks/')
        returned = json.loads(response.content.decode('utf-8'))
        for status, val in returned['tasks'].items():
            if status == non_empty_status:
                self.assertTrue(len(val) > 0)
            else:
                self.assertTrue(len(val) == 0)

    def test_reviewer_task_assignment(self):
        # there is a review task for user 1
        response = (self.clients[1].get(
            '/orchestra/api/interface/new_task_assignment/reviewer/'))
        self.assertEquals(response.status_code, 200)

        returned = json.loads(response.content.decode('utf-8'))
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': returned['id']},
            Task.objects.get(id=returned['id']).project.short_description,
            'Processing', 'Reviewing', True,
            False, {'test_key': 'test_value'})

    def test_save_entry_level_task_assignment(self):
        # user 0 only has certification for entry level tasks
        response = (self.clients[0].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))
        task_id = returned['id']
        task = Task.objects.get(id=task_id)

        # incorrect task id
        response = self.clients[0].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': -1,
                        'task_data': 'test'}),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'No task for given id')

        # user does not have a permission to save
        response = self.clients[1].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': task_id,
                        'task_data': 'test'}),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Worker is not associated with task')

        # save new info
        new_data = {'new_test_key': 'new_test_value'}
        response = self.clients[0].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': task_id,
                        'task_data': new_data}),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)

        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task_id},
            task.project.short_description,
            'Processing', 'Processing', False,
            False, new_data)

    def test_save_reviewer_task_assignment(self):
        new_data = {'new_test_key': 'new_test_value'}

        # get a reviewer task
        response = (self.clients[1].get(
            '/orchestra/api/interface/new_task_assignment/reviewer/'))
        self.assertEquals(response.status_code, 200)

        returned = json.loads(response.content.decode('utf-8'))

        task_id = returned['id']
        task = Task.objects.get(id=task_id)

        # entry level worker can't update the data
        response = self.clients[0].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': task_id,
                        'task_data': new_data}),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Worker is not allowed to save')

        reviewer_data = {'reviewer_key': 'reviewer_value'}

        # reviewer can update the data
        response = self.clients[1].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': task_id,
                        'task_data': reviewer_data}),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)

        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task_id},
            task.project.short_description,
            'Processing', 'Reviewing', True,
            False, reviewer_data)

    def test_submit_entry_level_task_assignment(self):
        # user 0 only has certification for entry level tasks
        response = (self.clients[0].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))
        task_id = returned['id']
        task = Task.objects.get(id=task_id)

        # user is not assigned to a task
        response = self._submit_assignment(self.clients[1], task_id)
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Task assignment with worker is in broken state.')

        # task does not exist
        response = self._submit_assignment(self.clients[1], -1)
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'No task for given id')

        # user 0 can only submit a task not accept
        response = self._submit_assignment(
            self.clients[0], task_id, command='accept')
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Only reviewer can accept the task.')

        # user 0 can only submit a task not reject
        response = self._submit_assignment(
            self.clients[0], task_id, command='reject')
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Only reviewer can reject the task.')

        # user 0 can't call illegal commands
        response = self._submit_assignment(
            self.clients[0], task_id, command='approve')
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Illegal command')
        data = {'submit_key1': 'submit_val1'}

        # user 0 can't submit a task if its submission prerequisites aren't
        # complete
        workflow = get_workflow_by_slug(task.project.workflow_slug)
        step = workflow.get_step(task.step_slug)
        step.submission_depends_on = [Step(slug='imaginary_test_step')]
        response = self._submit_assignment(
            self.clients[0], task_id)
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Submission prerequisites are not complete.')
        step.submission_depends_on = []

        data = {'submit_key1': 'submit_val1'}
        # user 0 submits a task
        response = self._submit_assignment(
            self.clients[0], task_id, data=data)
        self.assertEquals(response.status_code, 200)

        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task_id},
            task.project.short_description,
            'Submitted', 'Pending Review', False,
            True, data, work_times_seconds=[1])

        # user cannot resubmit a task
        response = self._submit_assignment(
            self.clients[0], task_id)
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Worker is not allowed to submit')

    def test_submit_reviewer_task_assignment(self):
        data = {'submit_key1': 'submit_val1'}

        # user 1 is picking up a task as a reviewer
        response = (self.clients[1].get(
            '/orchestra/api/interface/new_task_assignment/reviewer/'))
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))
        task_id = returned['id']
        task = Task.objects.get(id=task_id)
        rejected_data = {'rejected_key': 'rejected_val'}

        self.assertEquals(task_id, self.tasks['review_task'].id)

        # user 0 can retrieve data, but should see a read-only interface
        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task_id},
            task.project.short_description,
            'Submitted', 'Reviewing', False,
            True, {'test_key': 'test_value'})

        # user 1 should be able to review the post
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task_id},
            task.project.short_description,
            'Processing', 'Reviewing', True,
            False, {'test_key': 'test_value'})

        # user 1 can't submit a task
        response = self._submit_assignment(
            self.clients[1], task_id, data=data)
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Worker can only submit a task.')

        # user 1 rejects a task
        response = self._submit_assignment(
            self.clients[1], task_id, data=rejected_data, command='reject')
        self.assertEquals(response.status_code, 200)

        # user 0 should have the task back
        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task_id},
            task.project.short_description,
            'Processing', 'Post-review Processing', False,
            False, rejected_data)

        # user 1 should no longer be able to modify the post
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task_id},
            task.project.short_description,
            'Submitted', 'Post-review Processing', True,
            True, rejected_data, work_times_seconds=[1])

        # user 0 submits an updated data
        response = self._submit_assignment(
            self.clients[0], task_id, data=data)
        self.assertEquals(response.status_code, 200)

        # check if the data is saved
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task_id},
            task.project.short_description,
            'Processing', 'Reviewing', True,
            False, data, work_times_seconds=[1])

        accepted_data = {'accepted_key': 'accepted_val'}
        # user 1 accepts a task
        response = self._submit_assignment(
            self.clients[1], task_id, data=accepted_data, command='accept')
        self.assertEquals(response.status_code, 200)

        # check if the accepted_data is saved
        # and task is pending for a second review.
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task_id},
            task.project.short_description,
            'Submitted', 'Pending Review', True,
            True, accepted_data, work_times_seconds=[1, 1])

        # make sure a task can't be submitted twice
        response = self._submit_assignment(
            self.clients[1], task_id, command='accept')
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Worker is not allowed to submit')

        # user4 is picking up a task as a reviewer
        response = (self.clients[3].get(
            '/orchestra/api/interface/new_task_assignment/reviewer/'))
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['id'],
                          task_id)

        rejected_data = {'rejected_key': 'rejected_val'}

        # user4 rejects a task
        response = self._submit_assignment(
            self.clients[3], task_id, data=rejected_data, command='reject')
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))

        # check if the rejected_data is saved
        self._verify_good_task_assignment_information(
            self.clients[3], {'task_id': task_id},
            task.project.short_description,
            'Submitted', 'Post-review Processing', True,
            True, rejected_data, work_times_seconds=[1])

        # check client dashboards
        self._check_client_dashboard_state(self.clients[0], 'pending_review')

        self._check_client_dashboard_state(self.clients[1], 'returned')

        self._check_client_dashboard_state(self.clients[3],
                                           'pending_processing')

        response = self._submit_assignment(
            self.clients[1], task_id)
        self.assertEquals(response.status_code, 200)

        # check if client dashboards were updated
        self._check_client_dashboard_state(self.clients[0], 'pending_review')

        self._check_client_dashboard_state(self.clients[1], 'pending_review')

        self._check_client_dashboard_state(self.clients[3], 'in_progress')

        # check if the accepted_data is saved
        response = self._submit_assignment(
            self.clients[3], task_id, data=accepted_data, command='accept')
        self.assertEquals(response.status_code, 200)
        returned = json.loads(response.content.decode('utf-8'))

        # check if task is complete
        self._verify_good_task_assignment_information(
            self.clients[3], {'task_id': task_id},
            task.project.short_description,
            'Submitted', 'Complete', True,
            True, accepted_data, work_times_seconds=[1, 1])

        # check that reviewer cannot reaccept task
        response = self._submit_assignment(
            self.clients[3], task_id, data=accepted_data, command='accept')
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          'Task already completed')

    def test_assignment_snapshot_upgrades(self):
        good_snapshots = {
            'snapshots': [{
                'data': {},
                'datetime': datetime.utcnow().isoformat(),
                'type': TaskAssignment.SnapshotType.SUBMIT,
                'work_time_seconds': 1
            }],
            '__version': 1}
        old_snapshots = {
            'snapshots': [
                {
                    'data': {},
                    'datetime': datetime.utcnow().isoformat(),
                    'type': TaskAssignment.SnapshotType.SUBMIT,
                }, {
                    'data': {},
                    'datetime': datetime.utcnow().isoformat(),
                    'type': TaskAssignment.SnapshotType.SUBMIT,
                    'work_time_seconds': 1
                }]}
        upgraded_snapshots = deepcopy(old_snapshots)
        upgraded_snapshots['__version'] = 1
        upgraded_snapshots['snapshots'][0]['work_time_seconds'] = 0

        self.assertEquals(load_snapshots(good_snapshots), good_snapshots)
        self.assertEquals(load_snapshots(old_snapshots), upgraded_snapshots)

    def test_task_timing(self):
        """
        Ensure that timing information is properly recorded across
        submissions/rejections/acceptances.
        """
        task = self.tasks['rejected_review']

        self._submit_assignment(
            self.clients[6], task.id, seconds=35)

        self._submit_assignment(
            self.clients[7], task.id, command='reject', seconds=36)

        self._submit_assignment(
            self.clients[6], task.id, seconds=37)

        self._submit_assignment(
            self.clients[7], task.id, command='accept', seconds=38)

        self._verify_good_task_assignment_information(
            self.clients[6], {'task_id': task.id},
            task.project.short_description,
            'Submitted', 'Complete', False,
            True, {'test': 'test'},
            work_times_seconds=[35, 37])

        self._verify_good_task_assignment_information(
            self.clients[7], {'task_id': task.id},
            task.project.short_description,
            'Submitted', 'Complete', True,
            True, {'test': 'test'},
            work_times_seconds=[36, 38])

    def _verify_bad_task_assignment_information(
            self, client, post_data, error_message):
        response = client.post(
            '/orchestra/api/interface/task_assignment_information/',
            json.dumps(post_data),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        returned = json.loads(response.content.decode('utf-8'))
        self.assertEquals(returned['message'],
                          error_message)

    def _verify_good_task_assignment_information(
            self, client, post_data, project_description,
            assignment_status, task_status, is_reviewer,
            is_read_only, task_data, work_times_seconds=None):
        if work_times_seconds is None:
            work_times_seconds = []
        response = client.post(
            '/orchestra/api/interface/task_assignment_information/',
            json.dumps(post_data),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)

        task = Task.objects.get(id=post_data['task_id'])
        returned = json.loads(response.content.decode('utf-8'))
        expected = {'project': {'details': project_description,
                                'id': task.project.id,
                                'project_data': {},
                                'review_document_url': None},
                    'status': assignment_status,
                    'task': {'data': task_data, 'status': task_status},
                    'task_id': task.id,
                    'workflow': {
                        'slug': 'test_workflow', 'name': 'The workflow'},
                    'prerequisites': {},
                    'step': {'slug': 'step1', 'name': 'The first step'},
                    'is_reviewer': is_reviewer,
                    'is_read_only': is_read_only,
                    'work_times_seconds': work_times_seconds}
        self.assertEquals(returned, expected)

    def _submit_assignment(self, client, task_id, data=None,
                           seconds=1, command='submit'):
        if data is None:
            data = {'test': 'test'}
        request = json.dumps(
            {'task_id': task_id, 'task_data': data, 'command_type': command,
             'work_time_seconds': seconds})

        return client.post(
            '/orchestra/api/interface/submit_task_assignment/',
            request,
            content_type='application/json')
