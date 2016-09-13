from contextlib import contextmanager
from datetime import timedelta
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
    """

    timeout_timedelta = timedelta(minutes=2)
    verbose = True

    def __init__(self, args=None, kwargs=None):
        """
        args: list of arguments for the `runnable`
        kwargs: dictionary of arguments for the `runnable`
        timeout_timedelta: maximum number of seconds task can run
        verbose: boolean specifying if failures are logged
        """

        if args is None:
            args = []
        self.args = args

        if kwargs is None:
            kwargs = {}
        self.kwargs = kwargs

    def run(self, *args, **kwargs):
        """
        Abstract method to fill in with task work.
        """
        pass

    def on_error(self, e):
        """
        Runs if an exception occurs
        """
        pass

    def on_success(self):
        """
        Runs upon successful task success
        """
        pass

    def on_completion(self):
        """
        Runs upon task success
        """
        pass

    def process(self):
        try:
            timeout_seconds = self.timeout_timedelta.total_seconds()
            with timeout(self.run, timeout_seconds) as run:
                run(*self.args, **self.kwargs)
        except Exception as e:
            if self.verbose:
                if isinstance(e, TimeoutError):
                    logger.error('SafeTask timed out: %s', e, exc_info=True)
                else:
                    logger.error('Error running SafeTask: %s',
                                 e, exc_info=True)
            self.on_error(e)
        else:
            self.on_success()
        finally:
            self.on_completion()
