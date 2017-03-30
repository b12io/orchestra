from unittest.mock import patch

from orchestra.models import Iteration
from orchestra.models import Project
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.utils.project_properties import completed_projects
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_lifecycle import submit_task


class ProjectPropertiesTestCase(OrchestraTestCase):

    def setUp(self):
        super().setUp()
        setup_models(self)

    def test_completed_projects(self):
        projects = Project.objects.all()
        initial_task = assign_task(self.workers[6].id,
                                   self.tasks['awaiting_processing'].id)
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            initial_task = submit_task(initial_task.id, {},
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[6])
        self.assertEqual(completed_projects(projects).count(), 0)

        next_task = assign_task(
            self.workers[6].id,
            initial_task.project.tasks.order_by('-start_datetime')[0].id)
        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            initial_task = submit_task(next_task.id, {},
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[6])
        self.assertEqual(completed_projects(projects).count(), 0)

        next_task = assign_task(
            self.workers[6].id,
            initial_task.project.tasks.order_by('-start_datetime')[0].id)

        with patch('orchestra.utils.task_lifecycle._is_review_needed',
                   return_value=False):
            initial_task = submit_task(next_task.id, {},
                                       Iteration.Status.REQUESTED_REVIEW,
                                       self.workers[6])
        self.assertEqual(completed_projects(projects).count(), 1)
