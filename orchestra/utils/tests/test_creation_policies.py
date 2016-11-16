from unittest.mock import patch

from orchestra.models import Iteration
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import create_subsequent_tasks
from orchestra.utils.task_lifecycle import submit_task


def never_create(prerequisite_data, project_data, **kwargs):
    return False


class CreationPolicyTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)

    def test_always_create_policy(self):
        project = self.projects['creation_policy']

        # Create first task in test project
        create_subsequent_tasks(project)
        self.assertEqual(project.tasks.count(), 1)

        # Assign initial task to worker 0
        initial_task = assign_task(self.workers[0].id,
                                   project.tasks.first().id)
        # Submit task; next task should not be created, it never is
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            initial_task = submit_task(initial_task.id, {},
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[0])

        self.assertEqual(project.tasks.count(), 1)
