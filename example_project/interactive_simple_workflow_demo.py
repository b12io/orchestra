from pprint import pprint
from time import sleep

import argparse
import os
import subprocess
import sys

# Set up the standalone Django script
proj_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "../")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "example_project.settings")
sys.path.append(proj_path)
from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()

from orchestra.orchestra_api import create_orchestra_project
from orchestra.orchestra_api import get_project_information

FAST_MODE = True


def pause(n_seconds):
    if not FAST_MODE:
        sleep(n_seconds)


def run_demo():
    intro()
    describe_workflow()
    project_id = create_project()
    project_info_1(project_id)
    rating_task()
    project_info_2(project_id)
    conclusion()


def intro():
    subprocess.call('clear')
    print('----------------------------------------------')
    print('Welcome to the Orchestra Simple Workflow Demo.')
    print('----------------------------------------------')
    pause(2)
    print('In this demo, we will create a new project using the "Simple '
          'Workflow" workflow,')
    pause(2)
    print('which automatically extracts an image from a '
          'url and asks a human expert to rate it.')
    pause(2)
    ack = input('Are you ready to begin? (y/n): ').lower()
    while ack not in ['y', 'n']:
        ack = input('Please respond with "y" or "n": ').lower()
    if ack == 'n':
        print('Ok, maybe some other time!')
        sys.exit()
    print('Great!')


def describe_workflow():
    print('')
    print('The Simple Workflow has two steps, one automated and one human.')
    pause(2)
    print('The automated step takes a URL and extracts a random image from '
          'the page.')
    pause(2)
    print('The human step asks an expert to rate how "awesome" the image is '
          'on a scale from one to five.')
    pause(2)
    print('For this demo, we will scrape an image from www.josephbotros.com, '
          'the homepage of one of our visionary developers.')
    pause(2)
    print('If you open that URL in a browser, it should be pretty obvious '
          'which image the task will scrape.')
    pause(2)


def create_project():
    print('')
    print("Let's start by creating a new project that uses the workflow.")
    pause(2)
    print("We'll use the 'create_orchestra_project' API call.")
    pause(2)
    print('The API call looks like this:')
    print('''
create_orchestra_project(
  'simple_workflow',                       # The slug representing our workflow
  'A test run of our simple workflow',     # A description of the new project
  10,                                      # A priority level for the project
  {
    'url': 'http://www.josephbotros.com/'  # Data required by the workflow:
  },
)
    ''')
    pause(4)
    print('Make sure you have the example project running in another window '
          '(`python manage.py runserver`).')
    input('Press enter when you are ready to make the API call, which will '
          'create a new project and print out its id. ')

    project_id = create_orchestra_project(
        None,
        'simple_workflow',
        'A test run of our simple workflow',
        10,
        {
            'url': 'http://www.josephbotros.com/'
        },
        'https://docs.google.com/document/d/1s0IJycNAwHtZfsUwyo6lCJ7kI9pTOZddcaiRDdZUSAs',  # noqa
        'train',
    )
    print('Project with id {} created!'.format(project_id))
    pause(2)
    return project_id


def project_info_1(project_id):
    print('')
    print('When we created our project, it immediately ran the first step of '
          'the workflow: scraping an image from the website we passed in.')
    pause(2)
    print("Let's verify that this worked successfully by using Orchestra's "
          "API to check the project info.")
    pause(2)
    print('The API call looks like this:')
    print('')
    print('get_project_information(project_id)')
    print('')
    pause(2)
    input('Press enter when you are ready to make the API call and print out '
          'the JSON data received in response. ')

    project_info = get_project_information(project_id)
    print("Information received! Here's what we got:")
    print('')
    pause(2)
    pprint(project_info)
    pause(4)
    print('')
    print("Note that 'tasks.crawl.status' is 'Complete', and "
          "'tasks.crawl.latest_data.image' is set to an image URL scraped "
          "from our site. Paste the URL into a browser and you should see "
          "Joseph's smiling face!")
    pause(2)
    print("Also, check out 'tasks.rate'. That's the human step we'll need to "
          "do next. Observe that its status is 'Awaiting Processing' and "
          "that 'latest_data' is None because no work has been done yet.")
    pause(4)


def rating_task():
    print('')
    print("Let's fix that! It's time to work on the second step in our "
          "workflow: rating the image.")
    pause(2)
    print("In a browser window, log into Orchestra as a worker at "
          "127.0.0.1:8000/orchestra/app. If you haven't created a worker "
          "account yet, you can log in as the demo worker: username 'demo' "
          "and password 'demo'.")
    pause(2)
    print("Then, click the 'New delivery task' button to get the rating task "
          "assigned to you, and rate the photo to complete the task.")
    pause(2)
    print("When you're happy with your rating, click 'Submit' at the bottom "
          "of the page.")
    pause(2)
    input('Press enter when you have submitted the task. ')


def get_rating_info(msg, project_id):
    input(msg)
    project_info = get_project_information(project_id)
    complete = project_info['tasks']['rate']['status'] == 'Complete'
    rating = (project_info['tasks']['rate']['latest_data'].get('rating')
              if complete else None)
    print('')
    print("Information received! Here's what we got:")
    pause(2)
    print('')
    pprint(project_info)
    print('')
    pause(4)

    return complete, rating


def project_info_2(project_id):
    print('')
    print('Well done. You have completed your first Orchestra project!')
    pause(2)
    print("Let's verify that your rating was stored successfully by using "
          "Orchestra's API to check the project info again.")
    pause(2)
    print('As a reminder, the API call looks like this:')
    print('')
    print('get_project_information(project_id)')
    print('')
    pause(2)

    complete, rating = get_rating_info(
        'Press enter when you are ready to make the API call and print out '
        'the resulting JSON data. ', project_id)

    while not complete:
        print("Uh oh! It looks like the task did not get completed (see "
              "'tasks.rate.status' in the output above.)")
        pause(2)
        complete, rating = get_rating_info(
            'Press enter to try again, or CTRL-C to exit. ', project_id)

    print("Task complete! Note that 'tasks.rate.status' is 'Complete' in the "
          "output above.")
    pause(2)
    if not rating:
        print('Uh oh! Looks like you submitted the task without rating the '
              "image. (see 'tasks.rate.latest_data' in the output above.)")
        pause(2)
        print('We probably should have validated that :-)')
    else:
        print("Note that 'tasks.rate.latest_data.rating' is set to '{}', the "
              "rating you selected.".format(rating))
    pause(4)


def conclusion():
    print('')
    print('')
    print("Congratulations! Now you're ready to start building workflows of "
          "your own!")
    pause(2)
    print("To see a more in-depth explanation of how workflows are built, "
          "check out our illustrative workflow at "
          "http://orchestra.readthedocs.org/en/latest/example_use.html.")
    pause(2)
    print('We hope you enjoyed this tutorial, and welcome to the Orchestra '
          'community.')
    pause(2)
    print('Goodbye for now!')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-s', '--slow', action='store_true',
                        help='Display text fast.')
    args = parser.parse_args()
    FAST_MODE = not args.slow
    run_demo()
