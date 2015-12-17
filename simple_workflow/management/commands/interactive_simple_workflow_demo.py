from pprint import pprint
import subprocess
from time import sleep

from django.core.management.base import BaseCommand

from orchestra.orchestra_api import create_orchestra_project
from orchestra.orchestra_api import get_project_information


class Command(BaseCommand):
    help = 'Walks through the simple demo workflow'

    def add_arguments(self, parser):
        parser.add_argument('-s', '--slow', action='store_true', default=False,
                            help='Slow down text printouts for readability.')

    def handle(self, *args, **options):
        self.fast_mode = not options['slow']
        continue_demo = self.intro()
        if not continue_demo:
            return

        self.describe_workflow()
        project_id = self.create_project()
        self.project_info_1(project_id)
        self.rating_task()
        self.project_info_2(project_id)
        self.conclusion()

    def pause(self, n_seconds):
        if not self.fast_mode:
            sleep(n_seconds)

    def intro(self):
        subprocess.call('clear')
        print('----------------------------------------------')
        print('Welcome to the Orchestra Simple Workflow Demo.')
        print('----------------------------------------------')
        self.pause(2)
        print('In this demo, we will create a new project using the "Simple '
              'Workflow" workflow,')
        self.pause(2)
        print('which automatically extracts an image from a '
              'url and asks a human expert to rate it.')
        self.pause(2)
        ack = input('Are you ready to begin? (y/n): ').lower()
        while ack not in ['y', 'n']:
            ack = input('Please respond with "y" or "n": ').lower()
        if ack == 'n':
            print('Ok, maybe some other time!')
            return False
        print('Great!')
        return True

    def describe_workflow(self):
        print('')
        print('The Simple Workflow has two steps, one automated and one '
              'human.')
        self.pause(2)
        print('The automated step takes a URL and extracts a random image '
              'from the page.')
        self.pause(2)
        print('The human step asks an expert to rate how "awesome" the image '
              'is on a scale from one to five.')
        self.pause(2)
        print('For this demo, we will scrape an image from www.jrbotros.com, '
              'the homepage of one of our visionary developers.')
        self.pause(2)
        print('If you open that URL in a browser, it should be pretty obvious '
              'which image the task will scrape.')
        self.pause(2)

    def create_project(self):
        print('')
        print("Let's start by creating a new project that uses the workflow.")
        self.pause(2)
        print("We'll use the 'create_orchestra_project' API call.")
        self.pause(2)
        print('The API call looks like this:')
        print('''
create_orchestra_project(
    'simple_workflow',                       # The slug representing our workflow  # noqa
    'v1',                                    # The version of the workflow to use  # noqa
    'A test run of our simple workflow',     # A description of the new project
    10,                                      # A priority level for the project
    {
        'url': 'http://www.jrbotros.com/'    # Data required by the workflow:
    },
)
        ''')
        self.pause(4)
        print('Make sure you have the example project running in another '
              'window (`python manage.py runserver`).')
        input('Press enter when you are ready to make the API call, which '
              'will create a new project and print out its id. ')

        project_id = create_orchestra_project(
            None,
            'simple_workflow',
            'v1',
            'A test run of our simple workflow',
            10,
            {
                'url': 'http://www.jrbotros.com/'
            },
            'train',
        )
        print('Project with id {} created!'.format(project_id))
        self.pause(2)
        return project_id

    def project_info_1(self, project_id):
        print('')
        print('When we created our project, it immediately ran the first step '
              'of the workflow: scraping an image from the website we passed '
              'in.')
        self.pause(2)
        print("Let's verify that this worked successfully by using "
              "Orchestra's API to check the project info.")
        self.pause(2)
        print('The API call looks like this:')
        print('')
        print('get_project_information(project_id)')
        print('')
        self.pause(2)
        input('Press enter when you are ready to make the API call and print '
              'out the JSON data received in response. ')

        project_info = get_project_information(project_id)
        print("Information received! Here's what we got:")
        print('')
        self.pause(2)
        pprint(project_info)
        self.pause(4)
        print('')
        print("Note that 'tasks.crawl.status' is 'Complete', and "
              "'tasks.crawl.latest_data.image' is set to an image URL scraped "
              "from our site. Paste the URL into a browser and you should see "
              "Joseph's smiling face!")
        self.pause(2)
        print("Also, check out 'tasks.rate'. That's the human step we'll need "
              "to do next. Observe that its status is 'Awaiting Processing' "
              "and that 'latest_data' is None because no work has been done "
              "yet.")
        self.pause(4)

    def rating_task(self):
        print('')
        print("Let's fix that! It's time to work on the second step in our "
              "workflow: rating the image.")
        self.pause(2)
        print("In a browser window, log into Orchestra as a worker at "
              "127.0.0.1:8000/orchestra/app. If you haven't created a worker "
              "account yet, you can log in as the demo worker: username "
              "'demo' and password 'demo'.")
        self.pause(2)
        print("Then, click the 'New delivery task' button to get the rating "
              "task assigned to you, and rate the photo to complete the task.")
        self.pause(2)
        print("When you're happy with your rating, click 'Submit' at the "
              "bottom of the page.")
        self.pause(2)
        input('Press enter when you have submitted the task. ')

    def get_rating_info(self, msg, project_id):
        input(msg)
        project_info = get_project_information(project_id)
        complete = project_info['tasks']['rate']['status'] == 'Complete'
        rating = (project_info['tasks']['rate']['latest_data'].get('rating')
                  if complete else None)
        print('')
        print("Information received! Here's what we got:")
        self.pause(2)
        print('')
        pprint(project_info)
        print('')
        self.pause(4)

        return complete, rating

    def project_info_2(self, project_id):
        print('')
        print('Well done. You have completed your first Orchestra project!')
        self.pause(2)
        print("Let's verify that your rating was stored successfully by using "
              "Orchestra's API to check the project info again.")
        self.pause(2)
        print('As a reminder, the API call looks like this:')
        print('')
        print('get_project_information(project_id)')
        print('')
        self.pause(2)

        complete, rating = self.get_rating_info(
            'Press enter when you are ready to make the API call and print '
            'out the resulting JSON data. ', project_id)

        while not complete:
            print("Uh oh! It looks like the task did not get completed (see "
                  "'tasks.rate.status' in the output above.)")
            self.pause(2)
            complete, rating = self.get_rating_info(
                'Press enter to try again, or CTRL-C to exit. ', project_id)

        print("Task complete! Note that 'tasks.rate.status' is 'Complete' in "
              "the output above.")
        self.pause(2)
        if not rating:
            print("Uh oh! Looks like you submitted the task without rating "
                  "the image. (see 'tasks.rate.latest_data' in the output "
                  "above.)")
            self.pause(2)
            print('We probably should have validated that :-)')
        else:
            print("Note that 'tasks.rate.latest_data.rating' is set to '{}', "
                  "the rating you selected.".format(rating))
        self.pause(4)

    def conclusion(self):
        print('')
        print('')
        print("Congratulations! Now you're ready to start building workflows "
              "of your own!")
        self.pause(2)
        print("To see a more in-depth explanation of how workflows are built, "
              "check out our illustrative workflow at "
              "http://orchestra.readthedocs.org/en/latest/example_use.html.")
        self.pause(2)
        print('We hope you enjoyed this tutorial, and welcome to the '
              'Orchestra community.')
        self.pause(2)
        print('Goodbye for now!')
