import json

from django.test import override_settings
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import Step
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.iterations import verify_iterations
from orchestra.utils.load_json import load_encoded_json
from orchestra.utils.task_lifecycle import create_subsequent_tasks


class DashboardTestCase(OrchestraTestCase):

    def setUp(self):  # noqa
        super().setUp()
        setup_models(self)

    @override_settings(MACHINE_STEP_SCHEDULER={
        'path': ('orchestra.utils.machine_step_scheduler.'
                 'SynchronousMachineStepScheduler'),
    })
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

        human_step = self.workflow_steps['test_workflow_2']['step4']
        task = Task.objects.get(step=human_step, project=project)
        data = {'submit_key1': 'submit_val1'}

        # user 0 submits a task
        response = self._submit_assignment(self.clients[0], task.id, data=data)
        self.assertEquals(response.status_code, 200)

        # Machine Task was created
        self.assertEquals(Task.objects.filter(project=project).count(),
                          2)
        machine_step = self.workflow_steps['test_workflow_2']['simple_machine']
        machine_task_assignment = (
            TaskAssignment.objects
            .filter(task__step=machine_step,
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
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'No worker certificates')

        # user 0 only has certification for entry level tasks
        response = (self.clients[0].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))
        self.assertEquals(response.status_code, 200)
        returned = load_encoded_json(response.content)

        task = Task.objects.get(id=returned['id'])
        self.assertEquals({
            'id': task.id,
            'assignment_id': task.assignments.get(worker=self.workers[0]).id,
            'step': task.step.slug,
            'project': task.project.workflow_version.slug,
            'detail': task.project.short_description
        }, returned)

        # task assignment for invalid id should give bad request
        self._verify_bad_task_assignment_information(
            self.clients[0], {'task_id': -1},
            'Task matching query does not exist.')

        # task assignment for user3 not assigned to a task
        self._verify_bad_task_assignment_information(
            self.clients[2], {'task_id': task.id},
            'Worker is not associated with task')

        # task assignment is assigned to user 0
        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task.id},
            task.project.short_description,
            'Processing', 'Processing', False,
            False, {}, self.workers[0])

        # no more tasks for user 0 left
        response = (self.clients[0].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'No task')

    def _check_client_dashboard_state(self, client, non_empty_status):
        response = client.get('/orchestra/api/interface/dashboard_tasks/')
        returned = load_encoded_json(response.content)
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

        returned = load_encoded_json(response.content)
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': returned['id']},
            Task.objects.get(id=returned['id']).project.short_description,
            'Processing', 'Reviewing', True,
            False, {'test_key': 'test_value'}, self.workers[1])

    def test_save_entry_level_task_assignment(self):
        # user 0 only has certification for entry level tasks
        response = (self.clients[0].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))
        self.assertEquals(response.status_code, 200)
        returned = load_encoded_json(response.content)
        task = Task.objects.get(id=returned['id'])

        # incorrect task id
        response = self.clients[0].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': -1,
                        'task_data': 'test'}),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'No task for given id')

        # user does not have a permission to save
        response = self.clients[1].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': task.id,
                        'task_data': 'test'}),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'Worker is not associated with task')

        # save new info
        new_data = {'new_test_key': 'new_test_value'}
        response = self.clients[0].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': task.id,
                        'task_data': new_data}),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)

        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task.id},
            task.project.short_description,
            'Processing', 'Processing', False,
            False, new_data, self.workers[0])

    def test_save_reviewer_task_assignment(self):
        new_data = {'new_test_key': 'new_test_value'}

        # get a reviewer task
        response = (self.clients[1].get(
            '/orchestra/api/interface/new_task_assignment/reviewer/'))
        self.assertEquals(response.status_code, 200)

        returned = load_encoded_json(response.content)

        task = Task.objects.get(id=returned['id'])

        # entry level worker can't update the data
        response = self.clients[0].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': task.id,
                        'task_data': new_data}),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'Worker is not allowed to save')

        reviewer_data = {'reviewer_key': 'reviewer_value'}

        # reviewer can update the data
        response = self.clients[1].post(
            '/orchestra/api/interface/save_task_assignment/',
            json.dumps({'task_id': task.id,
                        'task_data': reviewer_data}),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)

        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task.id},
            task.project.short_description,
            'Processing', 'Reviewing', True,
            False, reviewer_data, self.workers[1])

    def test_submit_entry_level_task_assignment(self):
        # user 0 only has certification for entry level tasks
        response = (self.clients[0].get(
            '/orchestra/api/interface/new_task_assignment/entry_level/'))
        self.assertEquals(response.status_code, 200)
        returned = load_encoded_json(response.content)
        task = Task.objects.get(id=returned['id'])

        verify_iterations(task.id)

        # user is not assigned to a task
        response = self._submit_assignment(self.clients[1], task.id)
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'Task assignment with worker is in broken state.')

        # task does not exist
        response = self._submit_assignment(self.clients[1], -1)
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'No task for given id')

        # user 0 can only submit a task not reject
        response = self._submit_assignment(
            self.clients[0], task.id, command='reject')
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'Task not in rejectable state.')

        # user 0 can't call illegal commands
        response = self._submit_assignment(
            self.clients[0], task.id, command='approve')
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'Illegal command')
        data = {'submit_key1': 'submit_val1'}

        # user 0 can't submit a task if its submission prerequisites aren't
        # complete
        step = task.step
        step.submission_depends_on = [
            Step.objects.create(
                workflow_version=step.workflow_version,
                slug='imaginary_test_step',
                is_human=True,
            )
        ]
        step.save()
        response = self._submit_assignment(
            self.clients[0], task.id)
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'Submission prerequisites are not complete.')
        step.submission_depends_on = []
        step.save()

        data = {'submit_key1': 'submit_val1'}
        # user 0 submits a task
        response = self._submit_assignment(
            self.clients[0], task.id, data=data)
        self.assertEquals(response.status_code, 200)

        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task.id},
            task.project.short_description,
            'Submitted', 'Pending Review', False,
            True, data, self.workers[0])

        # Check that iteration has correct submitted state
        verify_iterations(task.id)

        # user cannot resubmit a task
        response = self._submit_assignment(
            self.clients[0], task.id)
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'Worker is not allowed to submit')

    def test_submit_reviewer_task_assignment(self):
        data = {'submit_key1': 'submit_val1'}

        # user 1 is picking up a task as a reviewer
        response = (self.clients[1].get(
            '/orchestra/api/interface/new_task_assignment/reviewer/'))
        self.assertEquals(response.status_code, 200)
        returned = load_encoded_json(response.content)
        task_id = returned['id']
        task = Task.objects.get(id=returned['id'])
        self.assertEquals(task.assignments.count(), 2)
        self.assertEquals(task_id, self.tasks['review_task'].id)

        verify_iterations(task.id)

        rejected_data = {'rejected_key': 'rejected_val'}

        # user 0 can retrieve data, but should see a read-only interface
        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task.id},
            task.project.short_description,
            'Submitted', 'Reviewing', False,
            True, {'test_key': 'test_value'}, self.workers[0])

        # user 1 should be able to review the post
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task.id},
            task.project.short_description,
            'Processing', 'Reviewing', True,
            False, {'test_key': 'test_value'}, self.workers[1])

        # user 1 rejects a task
        response = self._submit_assignment(
            self.clients[1], task_id, data=rejected_data, command='reject')
        self.assertEquals(response.status_code, 200)

        verify_iterations(task.id)

        # user 0 should have the task back
        self._verify_good_task_assignment_information(
            self.clients[0], {'task_id': task.id},
            task.project.short_description,
            'Processing', 'Post-review Processing', False,
            False, rejected_data, self.workers[0])

        # user 1 should no longer be able to modify the post
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task.id},
            task.project.short_description,
            'Submitted', 'Post-review Processing', True,
            True, rejected_data, self.workers[1])

        # user 0 submits an updated data
        response = self._submit_assignment(
            self.clients[0], task_id, data=data)
        self.assertEquals(response.status_code, 200)

        verify_iterations(task.id)

        # check if the data is saved
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task.id},
            task.project.short_description,
            'Processing', 'Reviewing', True,
            False, data, self.workers[1])

        accepted_data = {'accepted_key': 'accepted_val'}
        # user 1 accepts a task
        response = self._submit_assignment(
            self.clients[1], task_id, data=accepted_data, command='accept')
        self.assertEquals(response.status_code, 200)

        verify_iterations(task.id)

        # check if the accepted_data is saved
        # and task is pending for a second review.
        self._verify_good_task_assignment_information(
            self.clients[1], {'task_id': task.id},
            task.project.short_description,
            'Submitted', 'Pending Review', True,
            True, accepted_data, self.workers[1])

        # make sure a task can't be submitted twice
        response = self._submit_assignment(
            self.clients[1], task_id, command='accept')
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'Worker is not allowed to submit')

        # user 3 is picking up a task as a reviewer
        response = (self.clients[3].get(
            '/orchestra/api/interface/new_task_assignment/reviewer/'))
        self.assertEquals(response.status_code, 200)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['id'],
                          task.id)

        verify_iterations(task.id)

        rejected_data = {'rejected_key': 'rejected_val'}

        # user 3 rejects a task
        response = self._submit_assignment(
            self.clients[3], task_id, data=rejected_data, command='reject')
        self.assertEquals(response.status_code, 200)
        returned = load_encoded_json(response.content)

        verify_iterations(task.id)

        # check if the rejected_data is saved
        self._verify_good_task_assignment_information(
            self.clients[3], {'task_id': task.id},
            task.project.short_description,
            'Submitted', 'Post-review Processing', True,
            True, rejected_data, self.workers[3])

        # check client dashboards
        self._check_client_dashboard_state(self.clients[0], 'pending_review')

        self._check_client_dashboard_state(self.clients[1], 'returned')

        self._check_client_dashboard_state(self.clients[3],
                                           'pending_processing')

        response = self._submit_assignment(
            self.clients[1], task.id)
        self.assertEquals(response.status_code, 200)

        verify_iterations(task.id)

        # check if client dashboards were updated
        self._check_client_dashboard_state(self.clients[0], 'pending_review')

        self._check_client_dashboard_state(self.clients[1], 'pending_review')

        self._check_client_dashboard_state(self.clients[3], 'in_progress')

        # check if the accepted_data is saved
        response = self._submit_assignment(
            self.clients[3], task_id, data=accepted_data, command='accept')
        self.assertEquals(response.status_code, 200)
        returned = load_encoded_json(response.content)

        verify_iterations(task.id)

        # check if task is complete
        self._verify_good_task_assignment_information(
            self.clients[3], {'task_id': task.id},
            task.project.short_description,
            'Submitted', 'Complete', True,
            True, accepted_data, self.workers[3])

        # check that reviewer cannot reaccept task
        response = self._submit_assignment(
            self.clients[3], task_id, data=accepted_data, command='accept')
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          'Task already completed')

    def _verify_bad_task_assignment_information(
            self, client, post_data, error_message):
        response = client.post(
            '/orchestra/api/interface/task_assignment_information/',
            json.dumps(post_data),
            content_type='application/json')
        self.assertEquals(response.status_code, 400)
        returned = load_encoded_json(response.content)
        self.assertEquals(returned['message'],
                          error_message)

    def _verify_good_task_assignment_information(
            self, client, post_data, project_description,
            assignment_status, task_status, is_reviewer,
            is_read_only, task_data, worker):
        response = client.post(
            '/orchestra/api/interface/task_assignment_information/',
            json.dumps(post_data),
            content_type='application/json')
        self.assertEquals(response.status_code, 200)

        task = Task.objects.get(id=post_data['task_id'])
        returned = load_encoded_json(response.content)
        expected = {
            'project': {'details': project_description,
                        'id': task.project.id,
                        'project_data': {},
                        'team_messages_url': None},
            'status': assignment_status,
            'task': {'data': task_data, 'status': task_status},
            'task_id': task.id,
            'assignment_id': task.assignments.get(worker=worker).id,
            'workflow': {
                'slug': 'w1', 'name': 'Workflow One',
            },
            'workflow_version': {
                'slug': 'test_workflow', 'name': 'The workflow'},
            'prerequisites': {},
            'step': {'slug': 'step1', 'name': 'The first step'},
            'is_reviewer': is_reviewer,
            'is_read_only': is_read_only,
            'worker': {
                'username': worker.user.username,
                'first_name': worker.user.first_name,
                'last_name': worker.user.last_name,
            }
        }

        self.assertEquals(returned, expected)
