###########################################
Getting Started with Orchestra in 5 Minutes
###########################################

What follows is a simple 5-minute guide to getting up and running with
Orchestra that assumes some basic Python and Django experience, but not much
else. For a deeper introduction, you might want to check out our
:doc:`concepts`, and for in-depth information on using and developing with
Orchestra, take a look at our :doc:`API documentation <api>`.


********************
Install Dependencies
********************

Orchestra requires Python 3 and Django version 1.8 or higher to run, so make
sure you
`have them installed <https://docs.djangoproject.com/en/1.8/topics/install/>`_.
We recommend setting up a
`virtual environment <http://docs.python-guide.org/en/latest/dev/virtualenvs/>`_
to isolate your Python dependencies, and we're fond of
`virtualenvwrapper <https://virtualenvwrapper.readthedocs.org/en/latest/>`_ to
make that process easier. Make sure to create your virual environment with
Python 3 by passing ``--python=/path/to/bin/python3`` if it isn't your default
development setup.

Orchestra requires a number of Python dependencies to run. You can install them
by simply pulling down and installing our ``requirements.txt`` file::

  wget https://raw.githubusercontent.com/unlimitedlabs/orchestra/stable/requirements.txt
  pip install -r requirements.txt


***********************
Create a Django Project
***********************

Orchestra is a Django app, which means that it must be run within a Django
project (for more details, read `the Django tutorial
<https://docs.djangoproject.com/en/1.8/intro/tutorial01/#creating-a-project>`_
on this topic). Start a project with
``django-admin startproject your_project``, replacing ``your_project`` with
your favorite project name. From here on out, this document will assume that
you stuck with ``your_project``, and you should replace it appropriately.


*******************************
Install and Configure Orchestra
*******************************

Next, let's get Orchestra installed and running. To get the code, just install
using pip: ``pip install orchestra``.

Orchestra has a number of custom settings that require configuration before
use. First, download the default Orchestra settings file and place it next to
the project settings file::

  wget https://raw.githubusercontent.com/unlimitedlabs/orchestra/stable/example_project/example_project/orchestra_settings.py
  mv orchestra_settings.py your_project/your_project

Next, edit the ``orchestra_settings.py`` file:

* Add ``'simple_workflow'`` to ``settings.INSTALLED_APPS`` in the "General"
  section if you want to run the demo workflow
  (:ref:`instructions below <demo-section>`), and add ``'journalism_workflow'``
  if you want to run the :doc:`journalism workflow <example_use>`.

* Adjust your `email settings <https://docs.djangoproject.com/en/1.8/ref/settings/#std:setting-EMAIL_BACKEND>`_.
  By default, Orchestra will direct all messages to the console, but for a
  realistic registration workflow you'll want to set up a real mail server that
  can actually send emails.

* Change settings like the ``ORCHESTRA_PROJECT_API_SECRET`` from ``'CHANGEME'``
  to more appropriate values.

* Optionally, add 3rd party credentials in the "3rd Party Integrations" section
  so that Orchestra can store files on `Amazon S3
  <https://aws.amazon.com/s3/>`_ and use `Google Apps
  <http://apps.google.com>`_ and `Slack <https://slack.com/>`_ to help
  communicate with expert workers.

Then, at the bottom of your existing settings file
(``your_project/your_project/settings.py``), import the Orchestra
settings::

  from .orchestra_settings import setup_orchestra
  setup_orchestra(__name__)

You'll also need to set up Orchestra's URLs, so that Django knows where to
route users when they view Orchestra in the browser. If you don't have any URLs
of your own yet, you can just download our barebones example file with
``wget https://raw.githubusercontent.com/unlimitedlabs/orchestra/stable/example_project/example_project/urls.py``.

Alternatively, just make sure to add the following code inside the
``urlpatterns`` variable in ``your_project/your_project/urls.py``::

    # Admin Views
    url(r'^orchestra/admin/',
        include(admin.site.urls)),

    # Registration Views
    # Eventually these will be auto-registered with the Orchestra URLs, but for
    # now we need to add them separately.
    url(r'^orchestra/accounts/',
        include('registration.backends.default.urls')),

    # Optionally include these routes to enable user hijack functionality.
    url(r'^orchestra/switch/', include('hijack.urls')),

    # Logout then login is not available as a standard django
    # registration route.
    url(r'^orchestra/accounts/logout_then_login/$',
        auth_views.logout_then_login,
        name='logout_then_login'),

    # Orchestra URLs
    url(r'^orchestra/',
        include('orchestra.urls', namespace='orchestra')),

    # Beanstalk Dispatch URLs
    url(r'^beanstalk_dispatch/',
        include('beanstalk_dispatch.urls')),


Finally, you'll need to get the database set up. Create your database
with ``python manage.py migrate``. You'll also want to make sure you have an
initial worker account set up to try out example workflows. We've provided
several fixtures relevant for running our examples, which you can load with
``python manage.py loaddata <FIXTURE_NAME>``:

* 'demo_admin': creates a single admin account (username: ``admin``, password:
  ``admin``) suitable for logging in to the admin and managing the database.

* 'demo_worker': creates a single worker (username: ``demo``, password:
  ``demo``) suitable for running  the
  :ref:`simple demo workflow <demo-section>`.

* 'journalism_workflow': creates a number of accounts with certifications
  suitable for running our more complicated
  :doc:`journalism workflow <example_use>`.

In addition, you can use the Orchestra admin
(http://127.0.0.1:8000/orchestra/admin) to create new users and certifications
of your own at any time once Orchestra is running.

Now Orchestra should be ready to go! If you're confused about any of the above,
check out our barebones `example project <https://github.com/unlimitedlabs/orchestra/tree/stable/example_project>`_.

*************
Run Orchestra
*************

Now that Orchestra is configured, all that remains is to fire it up! Run your
Django project with ``python manage.py runserver`` (you'll want to switch to
something more robust in production, of course), and navigate to
``http://127.0.0.1:8000/orchestra/app`` in your favorite browser.

If you see the Orchestra sign-in page, your setup is working! Logging in as
the demo user we set up above should show you a dashboard with no available
tasks.

.. _demo-section:

****************************
Run the Example Project Demo
****************************

To give you a feel for what it means to run an Orchestra workflow from end to
end, we've included a very simple example workflow with two steps, one
machine and one human. The machine step takes a URL and extracts a random
image from the page. The human step asks an expert to rate how "awesome" the
image is on a scale from one to five. If you're interested in how we defined
the workflow, take a look at `the code <https://raw.githubusercontent.com/unlimitedlabs/orchestra/stable/simple_workflow/workflow.py>`_,
though we walk through a more interesting example in
:doc:`this documentation <example_use>`.

We've written an interactive script to walk through this simple workflow. To
run it:

* Make sure you added ``simple_workflow`` to your ``INSTALLED_APPS`` setting
  following the previous section.

* Pull down the script into your project's root directory (``your_project``,
  next to ``manage.py``)::

      wget https://raw.githubusercontent.com/unlimitedlabs/orchestra/stable/example_project/interactive_simple_workflow_demo.py

* Run the script::

      python interactive_simple_workflow_demo.py

The script will walk you through using :ref:`the Orchestra Client API
<client_api>` to create a new project based on the simple workflow, explaining
which API calls to use, what their output looks like, and how machine steps
interact with human steps and pass data back and forth.

If you don't want to go to the trouble of running the script yourself, take a
look at the :doc:`transcript of expected output <getting_started_transcript>`.
