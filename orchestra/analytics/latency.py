import itertools
from datetime import timedelta
from dateutil.parser import parse
from operator import attrgetter
from orchestra.models import Task
from orchestra.project_api.api import get_project_information
from orchestra.workflow import Step
from pandas import DataFrame


def work_time_df(projects):
    """
    Return projects' task assignment iteration timing information.

    The returned dataframe's schema is:
        project_id: the project's ID
        task_id: the task's ID
        assignment_level: a 1-indexed assignment counter (1 is entry-level, 2
            is first review, etc.)
        worker: the username of the worker on that assignment
        iteration: a work iteration for the assignment:
            - Iteration 0 represents the period from previous submission to
            reviewer assignment:
                - If this is the first assignment, 'previous submission'
                  means 'task creation'.
                - For iteration 0, work time will always be 0
                - If this task is auto-assigned, iteration 0's calendar time
                  will be close to 0.
            - Iterations N > 0 represent the period between a previous worker's
                input (submit/accept/reject) and the worker's submission.
        start_datetime: the time the iteration started.
        calendar_time: the wallclock time it took for the worker to complete
            that iteration.
        work_time: the amount of work time the worker reported dedicating to
            that iteration (0 for iteration 0).

    Args:
        projects (django.db.models.query.QuerySet):
            An iterable of projects to include in the report.

    Returns:
        df (pandas.DataFrame):
            A DataFrame with timing information.
    """
    # TODO(marcua): `get_project_information` per project means we do random
    # access all over the database.  Ideally, we'd have a sequential scan
    # version of this.
    time_data = list(itertools.chain.from_iterable(
        project_time_row_generator(
            get_project_information(project.id))
        for project in projects))
    df = DataFrame(time_data)
    return df


class Iteration(object):
    """ Represents a task assignment iteration's data for reporting. """
    def __init__(self, project, task, assignment, iteration, worker,
                 work_time, end_datetime):
        self.project = project
        self.task = task
        self.assignment = assignment
        self.iteration = iteration
        self.work_time = work_time
        self.end_datetime = end_datetime
        self.worker = worker

    def to_dict(self, start_datetime):
        return {
            'project_id': self.project['id'],
            'task_id': self.task['id'],
            'assignment_level': self.assignment,
            'iteration': self.iteration,
            'start_datetime': start_datetime,
            'work_time': self.work_time,
            'calendar_time': self.end_datetime - start_datetime,
            'worker': self.worker
        }


def project_time_row_generator(project_information):
    """
    Given a project, yields all task assignment iterations, reporting
    calendar and work times.
    """
    # lol at this variable name
    human_slugs = {
        step['slug'] for step in project_information['steps']
        if step['worker_type'] == Step.WorkerType.HUMAN}

    for step_slug, task in iter(project_information['tasks'].items()):
        # TODO(marcua): Eventually we'll want to support more fine-grained
        # task filtering for completed vs. in-progress tasks, or to
        # include machine tasks.
        if step_slug not in human_slugs:
            continue
        if task['status'] != dict(Task.STATUS_CHOICES)[Task.Status.COMPLETE]:
            continue
        iterations = []
        for assignment_idx, assignment in enumerate(task['assignments']):
            for iteration, snapshot in enumerate(
                    assignment['snapshots']['snapshots']):
                if iteration == 0:
                    iterations.append(Iteration(
                        project_information['project'], task,
                        assignment_idx + 1, 0, assignment['worker'],
                        timedelta(seconds=0),
                        parse(assignment['start_datetime'])))
                iterations.append(Iteration(
                    project_information['project'], task,
                    assignment_idx + 1,
                    iteration + 1,
                    assignment['worker'],
                    timedelta(seconds=snapshot['work_time_seconds']),
                    parse(snapshot['datetime'])))

        # To calculate calendar time, zip together each iteration
        # (in time-order) with the end time of the previous iteration
        # so that we can subtract the two.
        iterations = sorted(iterations, key=attrgetter('end_datetime'))
        iteration_times = (
            [parse(task['start_datetime'])] +
            [iteration.end_datetime for iteration in iterations])
        for start_datetime, iteration in zip(iteration_times[:-1], iterations):
            yield iteration.to_dict(start_datetime)
