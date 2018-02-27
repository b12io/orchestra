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

Orchestra requires Python 3 and Django version 1.11 or higher to run, so make
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

  wget https://raw.githubusercontent.com/b12io/orchestra/stable/requirements.txt
  pip install -r requirements.txt


***********************
Create a Django Project
***********************

Orchestra is a Django app, which means that it must be run within a Django
project (for more details, read `the Django tutorial
<https://docs.djangoproject.com/en/1.8/intro/tutorial01/#creating-a-project>`_
on this topic). Start a project with
``django-admin startproject your_project``, replacing ``your_project`` with
your favorite project name (but don't name it ``orchestra``, which will
conflict with our namespace). From here on out, this document will assume that
you stuck with ``your_project``, and you should replace it appropriately.


*******************************
Install and Configure Orchestra
*******************************

Next, let's get Orchestra installed and running. To get the code, just install
using pip: ``pip install orchestra``.

Orchestra has a number of custom settings that require configuration before
use. First, download the default Orchestra settings file and place it next to
the project settings file::

  wget https://raw.githubusercontent.com/b12io/orchestra/stable/example_project/example_project/orchestra_settings.py
  mv orchestra_settings.py your_project/your_project

Next, edit the ``orchestra_settings.py`` file:

* Add ``'simple_workflow'`` to ``settings.ORCHESTRA_WORKFLOWS`` in the "General"
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
  <https://aws.amazon.com/s3/>`_, use `Google Apps
  <http://apps.google.com>`_ and `Slack <https://slack.com/>`_ to help
  communicate with expert workers, and track usage
  in `Google Analytics <https://analytics.google.com/>`_.

Then, at the bottom of your existing settings file
(``your_project/your_project/settings.py``), import the Orchestra
settings::

  from .orchestra_settings import setup_orchestra
  setup_orchestra(__name__)

You'll also need to set up Orchestra's URLs, so that Django knows where to
route users when they view Orchestra in the browser. If you don't have any URLs
of your own yet, you can just download our barebones example file with
``wget https://raw.githubusercontent.com/b12io/orchestra/stable/example_project/example_project/urls.py``.

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
with ``python manage.py migrate``. You'll also want to make sure you have
loaded our example workflows and set up some user accounts to try them out.
To load the workflows, run::

    python manage.py loadworkflow <APP_LABEL> <WORKFLOW_VERSION>

Each of our example workflows provides a set of sample users already configured
with proper certifications. To load them, run::

    python manage.py loadworkflowsampledata <WORKFLOW_SLUG>/<WORKFLOW_VERSION>


If you would like to load all of the workflows, then run::

    python manage.py loadallworkflows

The example workflows we currently release with Orchestra are:

* A :ref:`simple demo workflow <demo-section>` with one human and one machine
  step. Its app label is ``simple_workflow``, its workflow slug is
  ``simple_workflow``, and the latest version is ``v1``.

* A more complicated :doc:`journalism workflow <example_use>`. Its app label
  is ``journalism_workflow``, its workflow slug is ``journalism``, and the
  latest version is ``v1``.

In addition, you can use the Orchestra admin
(http://127.0.0.1:8000/orchestra/admin) to create new users and certifications
of your own at any time once Orchestra is running. If you haven't created an
admin account for your Django project, you can load a sample one (username:
``admin``, password: ``admin``) with ``python manage.py loaddata demo_admin``.

We provide the option to use the third-party package `django-hijack
<https://github.com/arteria/django-hijack>`_ to act on behalf of users. To
enable this setting, ensure that the following setting is set
``HIJACK_ALLOW_GET_REQUESTS = True``, in addition to including the urls
referenced above.

Now Orchestra should be ready to go! If you're confused about any of the above,
check out our barebones `example project <https://github.com/b12io/orchestra/tree/stable/example_project>`_.

*************
Run Orchestra
*************

Now that Orchestra is configured, all that remains is to fire it up! Run your
Django project with ``python manage.py runserver`` (you'll want to switch to
something more robust in production, of course), and navigate to
``http://127.0.0.1:8000/orchestra/app`` in your favorite browser.

If you see the Orchestra sign-in page, your setup is working! If you loaded the
simple workflow's sample data above, logging in as its user (username ``demo``,
password ``demo``) should show you a dashboard with no available tasks.

.. _demo-section:

****************************
Run the Example Project Demo
****************************

To give you a feel for what it means to run an Orchestra workflow from end to
end, we've included a very simple example workflow with two steps, one
machine and one human. The machine step takes a URL and extracts a random
image from the page. The human step asks an expert to rate how "awesome" the
image is on a scale from one to five. If you're interested in how we defined
the workflow, take a look at `the code <https://raw.githubusercontent.com/b12io/orchestra/stable/simple_workflow/v1/version.json>`_,
though we walk through a more interesting example in
:doc:`this documentation <example_use>`.

We've written an interactive script to walk through this simple workflow. To
run it:

* Make sure you added ``simple_workflow`` to your ``ORCHESTRA_WORKFLOWS`` setting
  following the previous section.

* Make sure you loaded the workflow and its sample data following the previous
  section. This should have created a user with username ``demo`` and password
  ``demo``.

* Run the interactive walkthrough::

      python manage.py interactive_simple_workflow_demo

The script will walk you through using :ref:`the Orchestra Client API
<client_api>` to create a new project based on the simple workflow, explaining
which API calls to use, what their output looks like, and how machine steps
interact with human steps and pass data back and forth.

If you don't want to go to the trouble of running the script yourself, take a
look at the :doc:`transcript of expected output <getting_started_transcript>`.
