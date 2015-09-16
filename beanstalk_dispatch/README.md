The Beanstalk dispatcher is a Django app that runs functions that have
been scheduled to run an AWS SQS queue and executes them on Elastic
Beanstalk Worker machines that are listening to that queue.

## Configuration

To install:

  * create an Elastic Beanstalk environment for an application
that has the following two parameters in `settings.py`:

     ```python
     BEANSTALK_DISPATCH_SQS_KEY = 'your AWS key for accessing SQS'
     BEANSTALK_DISPATCH_SQS_SECRET = 'your AWS secret for accessing SQS'
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
            'a_function_to_dispatch': ('some_package.beanstalk_tasks', 'the_name_of_the_function_in_the_module')}
      ```

   The first line is a check we have that ensures this type of machine
should be a beanstalk worker.  We set a BEANSTALK_WORKER environment
variable to True in the environment's configuration only on our worker
machines.  This avoids other environments (e.g., our web servers) from
serving as open proxies for running arbitrary code.

   The second line is the dispatch table.  It maps function name (e.g.,
`a_function_to_dispatch`) to a module (e.g.,
`some_package.beanstalk_tasks` and function in that module (e.g.,
`the_name_of_the_function_in_the_module`).


## Scheduling a function to run

The `beanstalk_dispatch.client.schedule_function` schedules a function
to run on a given SQS queue.  The function name you pass it must be a
key in the `BEANSTALK_DISPATCH_TABLE`, and the queue name you pass it
must be a queue for which a beanstalk worker is configured.
