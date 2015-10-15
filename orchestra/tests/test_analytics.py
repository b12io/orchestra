from datetime import timedelta
from dateutil.parser import parse
from orchestra.analytics.latency import work_time_df
from orchestra.tests.helpers import OrchestraTestCase
from orchestra.tests.helpers.fixtures import setup_models
from orchestra.tests.helpers.fixtures import setup_task_history
from pandas import DataFrame
from pandas.util.testing import assert_frame_equal


class AnalyticsTestCase(OrchestraTestCase):
    def setUp(self):  # noqa
        super(AnalyticsTestCase, self).setUp()
        setup_models(self)

    def test_work_time_df(self):
        task = setup_task_history(self)
        returned = work_time_df([task.project])

        self.assertEquals(returned.project_id.nunique(), 1)
        self.assertEquals(returned.task_id.nunique(), 1)

        header = ['assignment_level', 'worker', 'iteration', 'start_datetime',
                  'calendar_time', 'work_time']
        expected = DataFrame(
            [(1, 'test_user_5', 0, parse('2015-10-12T01:00:00+00:00'), timedelta(hours=1), timedelta(seconds=0)),  # noqa
             (1, 'test_user_5', 1, parse('2015-10-12T02:00:00+00:00'), timedelta(minutes=2), timedelta(seconds=35)),  # noqa
             (2, 'test_user_6', 0, parse('2015-10-12T02:02:00+00:00'), timedelta(minutes=58), timedelta(seconds=0)),  # noqa
             (2, 'test_user_6', 1, parse('2015-10-12T03:00:00+00:00'), timedelta(minutes=1), timedelta(seconds=36)),  # noqa
             (1, 'test_user_5', 2, parse('2015-10-12T03:01:00+00:00'), timedelta(minutes=4), timedelta(seconds=37)),  # noqa
             (2, 'test_user_6', 2, parse('2015-10-12T03:05:00+00:00'), timedelta(minutes=2), timedelta(seconds=38)),  # noqa
             (3, 'test_user_7', 0, parse('2015-10-12T03:07:00+00:00'), timedelta(minutes=53), timedelta(seconds=0)),  # noqa
             (3, 'test_user_7', 1, parse('2015-10-12T04:00:00+00:00'), timedelta(minutes=2), timedelta(seconds=36)),  # noqa
             (2, 'test_user_6', 3, parse('2015-10-12T04:02:00+00:00'), timedelta(minutes=1), timedelta(seconds=35)),  # noqa
             (3, 'test_user_7', 2, parse('2015-10-12T04:03:00+00:00'), timedelta(minutes=10), timedelta(seconds=38)),  # noqa
            ],
            columns=header)

        assert_frame_equal(returned[header], expected)
