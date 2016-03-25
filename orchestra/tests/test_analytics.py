from datetime import timedelta
from dateutil.parser import parse
from orchestra.analytics.latency import calendar_time_sum
from orchestra.analytics.latency import work_time_sum
from orchestra.analytics.latency import work_time_df
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import setup_task_history
from pandas import concat
from pandas import DataFrame
from pandas.util.testing import assert_frame_equal


class AnalyticsTestCase(OrchestraTestCase):
    def setUp(self):  # noqa
        super().setUp()
        setup_models(self)

    def test_work_time_df(self):
        task = setup_task_history(self)
        returned = work_time_df([task.project])

        self.assertEquals(returned.project_id.nunique(), 1)
        self.assertEquals(returned.task_id.nunique(), 1)

        header = ['assignment_level', 'worker', 'iteration', 'start_datetime',
                  'end_datetime', 'calendar_time', 'work_time']
        expected = DataFrame(
            [(1, 'test_user_5', 0, parse('2015-10-12T01:00:00+00:00'), parse('2015-10-12T02:00:00+00:00'), timedelta(hours=1), timedelta(seconds=0)),  # noqa
             (1, 'test_user_5', 1, parse('2015-10-12T02:00:00+00:00'), parse('2015-10-12T02:02:00+00:00'), timedelta(minutes=2), timedelta(seconds=35)),  # noqa
             (2, 'test_user_6', 0, parse('2015-10-12T02:02:00+00:00'), parse('2015-10-12T03:00:00+00:00'), timedelta(minutes=58), timedelta(seconds=0)),  # noqa
             (2, 'test_user_6', 1, parse('2015-10-12T03:00:00+00:00'), parse('2015-10-12T03:01:00+00:00'), timedelta(minutes=1), timedelta(seconds=36)),  # noqa
             (1, 'test_user_5', 2, parse('2015-10-12T03:01:00+00:00'), parse('2015-10-12T03:05:00+00:00'), timedelta(minutes=4), timedelta(seconds=37)),  # noqa
             (2, 'test_user_6', 2, parse('2015-10-12T03:05:00+00:00'), parse('2015-10-12T03:07:00+00:00'), timedelta(minutes=2), timedelta(seconds=38)),  # noqa
             (3, 'test_user_7', 0, parse('2015-10-12T03:07:00+00:00'), parse('2015-10-12T04:00:00+00:00'), timedelta(minutes=53), timedelta(seconds=0)),  # noqa
             (3, 'test_user_7', 1, parse('2015-10-12T04:00:00+00:00'), parse('2015-10-12T04:02:00+00:00'), timedelta(minutes=2), timedelta(seconds=36)),  # noqa
             (2, 'test_user_6', 3, parse('2015-10-12T04:02:00+00:00'), parse('2015-10-12T04:03:00+00:00'), timedelta(minutes=1), timedelta(seconds=35)),  # noqa
             (3, 'test_user_7', 2, parse('2015-10-12T04:03:00+00:00'), parse('2015-10-12T04:13:00+00:00'), timedelta(minutes=10), timedelta(seconds=38)),  # noqa
            ],
            columns=header)

        expected['start_datetime'] = (
            expected['start_datetime'].astype('datetime64[ns]'))
        expected['end_datetime'] = (
            expected['end_datetime'].astype('datetime64[ns]'))

        assert_frame_equal(returned[header], expected)

    def test_work_time_sum(self):
        task = setup_task_history(self)
        df = work_time_df([task.project])

        header = ['work_time']
        expected = DataFrame(
            [(timedelta(minutes=4, seconds=15))],
            columns=header)
        returned = work_time_sum(df, ['project_id'])

        assert_frame_equal(returned[header], expected)

    def test_calendar_time_sum(self):
        task = setup_task_history(self)
        df = work_time_df([task.project])

        # Duplicate the amount of work completed by creating a ficitonal
        # second set of tasks.  The calendar times are the same, so the
        # project shouldn't have double the calendar time.
        duplicate = df.copy(deep=True)
        duplicate['task_id'] = duplicate.task_id + 1
        df = concat([df, duplicate])

        header = ['calendar_time']

        # Test grouping by project ID
        expected = DataFrame(
            [(timedelta(hours=3, minutes=13))],
            columns=header)
        returned = calendar_time_sum(df, ['project_id'])
        assert_frame_equal(returned[header], expected)

        # Test grouping by task ID
        expected = DataFrame(
            [(timedelta(hours=3, minutes=13),),
             (timedelta(hours=3, minutes=13),)],
            columns=header)
        returned = calendar_time_sum(df, ['project_id', 'task_id'])
        assert_frame_equal(returned[header], expected)
