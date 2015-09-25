----------------------------------------------
Welcome to the Orchestra Simple Workflow Demo.
----------------------------------------------

In this demo, we will create a new project using the "Simple Workflow" workflow,
which automatically extracts an image from a url and asks a human expert to rate
it. Are you ready to begin? (y/n): y
Great!

The Simple Workflow has two steps, one automated and one human.
The automated step takes a URL and extracts a random image from the page.
The human step asks an expert to rate how "awesome" the image is on a scale from one to five.
For this demo, we will scrape an image from www.josephbotros.com, the homepage of one of our visionary developers.
If you open that URL in a browser, it should be pretty obvious which image the task will scrape.

Let's start by creating a new project that uses the workflow.
We'll use the 'create_orchestra_project' API call.
The call looks like this::

  create_orchestra_project(
      'simple_workflow',                       # The slug representing our workflow
      'A test run of our simple workflow',     # A description of the new project
      10,                                      # A priority level for the project
      {
        'url': 'http://www.josephbotros.com/'  # Data required by the workflow:
      },
  )

Make sure you have the example project running in another window (``python manage.py runserver``).
Press enter when you are ready to make the call.
Project with id 5 created!

When we created our project, it immediately ran the first step of the workflow: scraping an image from the website we passed in.
Let's verify that this worked successfully by using Orchestra's API to check the project info.
The call looks like this::

  get_project_information(project_id)

Press enter when you are ready to make the call.
Information received! Here's what we got::

  {'project': {'id': 5,
               'priority': 10,
               'project_data': {'url': 'http://www.josephbotros.com/'},
               'review_document_url': 'https://docs.google.com/document/d/1s0IJycNAwHtZfsUwyo6lCJ7kI9pTOZddcaiRDdZUSAs',
               'short_description': 'A test run of our simple workflow',
               'start_datetime': '2015-09-25T17:51:14.784739Z',
               'task_class': 0,
               'workflow_slug': 'simple_workflow'},
   'steps': [['crawl', 'Find an awesome image on a website'],
             ['rate', 'Rate the image that we found']],
   'tasks': {'crawl': {'assignments': [{'id': 9,
                                        'in_progress_task_data': {'image': 'http://www.josephbotros.com/img/me.jpg',
                                                                  'status': 'success'},
                                        'snapshots': {'__version': 1,
                                                      'snapshots': []},
                                        'start_datetime': '2015-09-25T17:51:14.852160Z',
                                        'status': 'Submitted',
                                        'task': 9,
                                        'worker': None}],
                       'id': 9,
                       'latest_data': {'image': 'http://www.josephbotros.com/img/me.jpg',
                                       'status': 'success'},
                       'project': 5,
                       'status': 'Complete',
                       'step_slug': 'crawl'},
             'rate': {'assignments': [],
                      'id': 10,
                      'latest_data': None,
                      'project': 5,
                      'status': 'Awaiting Processing',
                      'step_slug': 'rate'}}}

Note that ``tasks.crawl.status`` is ``Complete``, and ``tasks.crawl.latest_data.image`` is set to an image URL scraped from our site. Paste the URL into a browser and you should see Joseph's smiling face!
Also, check out ``tasks.rate``. That's the human step we'll need to do next. Observe that it's status is ``Awaiting Processing`` and that ``latest_data`` is ``None`` because no work has been done yet.

Let's fix that! It's time to work on the second step in our workflow: rating the image.
In a browser window, log into Orchestra as a worker at ``127.0.0.1:8000/orchestra/app``. If you haven't created a worker account yet, you can log in as the demo worker: username ``demo`` and password ``demo``.
Then, click the 'New delivery task' button to get the rating task assigned to you, and rate the photo to complete the task.
When you're happy with your rating, click 'Submit' at the bottom of the page.
Press enter when you have submitted the task.

Well done. You have completed your first Orchestra project!
Let's verify that your rating was stored successfully by using Orchestra's API to check the project info again.
As a reminder, the call looks like this::

  get_project_information(project_id)

Press enter when you are ready to make the call.

Information received! Here's what we got::

  {'project': {'id': 5,
               'priority': 10,
               'project_data': {'url': 'http://www.josephbotros.com/'},
               'review_document_url': 'https://docs.google.com/document/d/1s0IJycNAwHtZfsUwyo6lCJ7kI9pTOZddcaiRDdZUSAs',
               'short_description': 'A test run of our simple workflow',
               'start_datetime': '2015-09-25T17:51:14.784739Z',
               'task_class': 0,
               'workflow_slug': 'simple_workflow'},
   'steps': [['crawl', 'Find an awesome image on a website'],
             ['rate', 'Rate the image that we found']],
   'tasks': {'crawl': {'assignments': [{'id': 9,
                                        'in_progress_task_data': {'image': 'http://www.josephbotros.com/img/me.jpg',
                                                                  'status': 'success'},
                                        'snapshots': {'__version': 1,
                                                      'snapshots': []},
                                        'start_datetime': '2015-09-25T17:51:14.852160Z',
                                        'status': 'Submitted',
                                        'task': 9,
                                        'worker': None}],
                       'id': 9,
                       'latest_data': {'image': 'http://www.josephbotros.com/img/me.jpg',
                                       'status': 'success'},
                       'project': 5,
                       'status': 'Complete',
                       'step_slug': 'crawl'},
             'rate': {'assignments': [{'id': 10,
                                       'in_progress_task_data': {'rating': '5'},
                                       'snapshots': {'__version': 1,
                                                     'snapshots': [{'data': {'rating': '5'},
                                                                    'datetime': '2015-09-25T17:52:03.575369',
                                                                    'type': 0,
                                                                    'work_time_seconds': 60}]},
                                       'start_datetime': '2015-09-25T17:51:48.647159Z',
                                       'status': 'Submitted',
                                       'task': 10,
                                       'worker': 'demo'}],
                      'id': 10,
                      'latest_data': {'rating': '5'},
                      'project': 5,
                      'status': 'Complete',
                      'step_slug': 'rate'}}}

Task complete! Note that ``tasks.rate.status`` is ``Complete`` in the output above.
Note that ``tasks.rate.latest_data.rating`` is set to ``5``, the rating you selected.


Congratulations! Now you're ready to start building workflows of your own!
To see a more in-depth explanation of how workflows are built, check out our
illustrative workflow in :doc:`the documentation <example_use>`.
We hope you enjoyed this tutorial, and welcome to the Orchestra community.
Goodbye for now!
