from contextlib import contextmanager
from datetime import timedelta
from django.conf import settings
from timeout_decorator import timeout as timeout_decorator
from timeout_decorator import TimeoutError

import logging
logger = logging.getLogger(__name__)


@contextmanager
def timeout(function, time):
    yield timeout_decorator(time)(function)


class SafeTask(object):
    """
    Runs a function within a `@timeout` decorator and catches any exceptions.
    timeout_timedelta: maximum number of seconds task can run
    verbose: boolean specifying if failures are logged
    """

    timeout_timedelta = getattr(settings,
                                'BEANSTALK_DISPATCH_TASK_TIMEOUT',
                                timedelta(minutes=2))
    verbose = True

    def run(self, *args, **kwargs):
        """
        Abstract method to fill in with task work
        """
        pass

    def on_error(self, e, *args, **kwargs):
        """
        Run if the task fails for any reason
        """
        pass

    def on_success(self, *args, **kwargs):
        """
        Run after the task completes successfully
        """
        pass

    def on_completion(self, *args, **kwargs):
        """
        Run after each task (after `on_error` or `on_success`)
        """
        pass

    def process(self, *args, **kwargs):
        """
        args: list of arguments for the `runnable`
        kwargs: dictionary of arguments for the `runnable`
        """
        try:
            timeout_seconds = self.timeout_timedelta.total_seconds()
            with timeout(self.run, timeout_seconds) as run:
                run(*args, **kwargs)
        except Exception as e:
            if self.verbose:
                if isinstance(e, TimeoutError):
                    logger.error('SafeTask timed out: %s', e, exc_info=True)
                else:
                    logger.error('Error running SafeTask: %s',
                                 e, exc_info=True)
            self.on_error(e, *args, **kwargs)
        else:
            self.on_success(*args, **kwargs)
        finally:
            self.on_completion(*args, **kwargs)
