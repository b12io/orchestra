import itertools
import numpy as np
from datetime import timedelta
from dateutil.parser import parse
from operator import attrgetter

from pandas import DataFrame

from orchestra.models import Task
from orchestra.project_api.api import get_project_information


def work_time_df(projects, human_only=True, complete_tasks_only=True):
    """
    Return projects' task assignment iteration timing information.

    The returned dataframe's schema is:
        project_id: the project's ID
        project_description: the project's human readable description
        task_id: the task's ID
        task_step_slug: the task's step slug
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
        end_datetime: the time the iteration ended.
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
            get_project_information(project.id),
            human_only, complete_tasks_only)
        for project in projects))
    df = DataFrame(time_data)
    # Pandas treats all non-primitives as strings, so we explicitly cast
    # datetimes as datetimes instead of strings.
    if not df.empty:
        df['start_datetime'] = df['start_datetime'].astype('datetime64[ns]')
        df['end_datetime'] = df['end_datetime'].astype('datetime64[ns]')
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
            'project_description': self.project['short_description'],
            'task_id': self.task['id'],
            'task_step_slug': self.task['step_slug'],
            'assignment_level': self.assignment,
            'iteration': self.iteration,
            'start_datetime': start_datetime,
            'work_time': self.work_time,
            'calendar_time': self.end_datetime - start_datetime,
            'end_datetime': self.end_datetime,
            'worker': self.worker
        }


def project_time_row_generator(project_information,
                               human_only,
                               complete_tasks_only):
    """
    Given a project, yields all task assignment iterations, reporting
    calendar and work times.
    """
    # lol at this variable name
    human_slugs = {
        step['slug'] for step in project_information['steps']
        if step['is_human']}

    for step_slug, task in iter(project_information['tasks'].items()):
        # TODO(marcua): Eventually we'll want to support more fine-grained
        # task filtering for completed vs. in-progress tasks, or to
        # include machine tasks.
        if human_only and step_slug not in human_slugs:
            continue
        if (complete_tasks_only
                and task['status'] !=
                dict(Task.STATUS_CHOICES)[Task.Status.COMPLETE]):
            continue
        iterations = []

        for assignment_idx, assignment in enumerate(task['assignments']):
            iterations.append(Iteration(
                project_information['project'], task,
                assignment_idx + 1, 0, assignment['worker']['username'],
                timedelta(seconds=0),
                parse(assignment['start_datetime'])))
            for iteration, snapshot in enumerate(
                    assignment['snapshots']['snapshots']):
                iterations.append(Iteration(
                    project_information['project'], task,
                    assignment_idx + 1,
                    iteration + 1,
                    assignment['worker']['username'],
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


def work_time_sum(df, dimensions):
    """
    Sums work time grouped by `dimensions`.

    Args:
        df (pandas.DataFrame):
            A DataFrame with a schema described in `work_time_df`.
        dimensions (list):
            A list of column names to group on. Example include any subset
            of `['project_id', 'project_description', 'task_id',
            'task_step_slug', 'assignment_level', 'iteration']`.

    Returns:
        df (pandas.DataFrame):
            A DataFrame with timing information.
    """
    return df.groupby(dimensions, as_index=False).agg({'work_time': np.sum})


def calendar_time_sum(df, dimensions):
    """
    Sums calendar time grouped by `dimensions`.

    Args:
        df (pandas.DataFrame):
            A DataFrame with a schema described in `work_time_df`.
        dimensions (list):
            A list of column names to group on. Example include any subset
            of `['project_id', 'project_description', 'task_id',
            'task_step_slug', 'assignment_level', 'iteration']`.

    Returns:
        df (pandas.DataFrame):
            A DataFrame with timing information.
    """
    if (dimensions == ['project_id'] or
            dimensions == ['project_description'] or
            set(dimensions) == {'project_id', 'project_description'}):
        # When reporting the project time, we want to avoid double-counting two
        # tasks that are running in parallel, so we calculate the difference
        # between the farthest-apart start and end times for iterations.
        aggregated = df.groupby(dimensions, as_index=False).agg({
            'start_datetime': np.min,
            'end_datetime': np.max})
        aggregated['calendar_time'] = (
            aggregated['end_datetime'] - aggregated['start_datetime'])
        aggregated.drop('start_datetime', axis=1, inplace=True)
        aggregated.drop('end_datetime', axis=1, inplace=True)
        return aggregated
    else:
        # For groupings that are more granular, like assignments, the work of
        # several workers is interspersed (e.g., worker 1 does work, then
        # worker 2 reviews, etc.). Computing the end time minus the start time
        # would allocate the same calendar time to multiple assignments, so we
        # want to sum up their computed calendar_datetimes.
        return df.groupby(dimensions, as_index=False).agg(
            {'calendar_time': np.sum})
