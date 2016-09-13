from contextlib import contextmanager
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

    def __init__(self, runnable=None, task_args=None, task_kwargs=None,
                 timeout_seconds=120, num_retries=0, verbose=True):
        """
        runnable: optional function to run
        task_args: list of arguments for the `runnable`
        task_kwargs: dictionary of arguments for the `runnable`
        timeout_seconds: maximum number of seconds task can run
        num_retries: number of times to try a failed task again
        verbose: boolean specifying if failures are logged
        """
        if runnable is not None:
            self.run = runnable
        if task_args is None:
            task_args = []
        if task_kwargs is None:
            task_kwargs = {}
        self.task_args = task_args
        self.task_kwargs = task_kwargs

        self.timeout_seconds = timeout_seconds
        self.num_retries = num_retries
        self.verbose = verbose

    def run(self, *args, **kwargs):
        """
        Default run method which runs the `runnable` function.
        """
        pass

    def on_error(self, e):
        """
        Runs if an exception occurs
        """
        if self.verbose:
            logger.warning(e, exc_info=True)

    def on_success(self):
        """
        Runs upon successful task success
        """
        pass

    def reschedule(self):
        """
        Abstract method for retrying a task
        """
        pass

    def on_complete(self):
        """
        Runs upon task success
        """
        pass

    def process(self):
        try:
            with timeout(self.run, self.timeout_seconds) as run:
                run(*self.task_args, **self.task_kwargs)
        except Exception as e:
            self.on_error(e)
            if self.num_retries > 0:
                self.num_retries -= 1
                self.reschedule()
            if self.verbose:
                if isinstance(e, TimeoutError):
                    logger.warning('Task timed out %s', e, exc_info=True)
        else:
            self.on_success()
        finally:
            self.on_completion()
