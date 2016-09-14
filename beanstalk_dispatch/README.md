The Beanstalk dispatcher is a Django app that runs functions that have
been scheduled to run an AWS SQS queue and executes them on Elastic
Beanstalk Worker machines that are listening to that queue.

## Configuration

To install:

  * create an Elastic Beanstalk environment for an application
that has the following two parameters in `settings.py`:

```python
     BEANSTALK_DISPATCH_SQS_KEY = 'your AWS key for accessing SQS'
     BEANSTALK_DISPATCH_SQS_SECRET = 'your AWS secret for accessing SQS
```

  * add `beanstalk_dispatch` to settings.py's `INSTALLED_APPS`

  * Add `url(r'^beanstalk_dispatch/',
    include('beanstalk_dispatch.urls')),` to your main `urls.py`

  * Add `/beanstalk_dispatch/dispatcher` as the HTTP endpoint or your
    beanstalk worker configuration in the AWS console.

  * Add a dispatch table.  The dispatcher works by creating an HTTP
endpoint that a local SQS/Beanstalk daemon POSTs requests to.  That
endpoint consults a `BEANSTALK_DISPATCH_TABLE`, which maps function
names onto functions to run.  Here's an example:

```python
      if os.environ.get('BEANSTALK_WORKER') == 'True':
        BEANSTALK_DISPATCH_TABLE = {
            'a_function_to_dispatch': ('some_package.beanstalk_tasks.'
                                      'the_name_of_the_function_in_the_module')
        }
```

   The first line is a check we have that ensures this type of machine
should be a beanstalk worker.  We set a `BEANSTALK_WORKER` environment
variable to True in the environment's configuration only on our worker
machines.  This avoids other environments (e.g., our web servers) from
serving as open proxies for running arbitrary code.

The second line is the dispatch table. It maps a path to the function to be
executed.


## Scheduling a function to run

The `beanstalk_dispatch.client.schedule_function` schedules a function
to run on a given SQS queue.  The function name you pass it must be a
key in the `BEANSTALK_DISPATCH_TABLE`, and the queue name you pass it
must be a queue for which a beanstalk worker is configured.

## Using SafeTasks

By default, every function run by `beanstalk_dispatch` is wrapped in a
`SafeTask` class that sets a `@timeout` decorator on the function and catches
any exceptions for logging. If you would like to customize the behavior of the
`SafeTask`, pass an instance in to `schedule_function` which contains your
function and have this run.

The following parameters/functions are configurable on a `SafeTask`

`timeout_timedelta`: maximum number of seconds task can run
`verbose`: boolean specifying if failures are logged
`run`: abstract method to fill in with task work
`on_error`: run if the task fails for any reason
`on_success`: run after the task completes successfully
`on_completion`: run after each task (after `on_error` or `on_success`)
