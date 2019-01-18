from pprint import pprint

from django.core.management.base import BaseCommand

from orchestra.orchestra_api import create_orchestra_project
from orchestra.orchestra_api import get_project_information


class Command(BaseCommand):
    help = 'Start and examine projects using the journalism workflow'

    def add_arguments(self, parser):
        parser.add_argument(
            '-p', '--project-id',
            help='Existing project id to check status of')
        primary_command_group = parser.add_mutually_exclusive_group(
            required=True)
        primary_command_group.add_argument(
            '-n', '--new', action='store_true',
            help='Start a new journalism project')
        primary_command_group.add_argument(
            '-s', '--status', action='store_true',
            help='Check the status of an in-progress project')
        primary_command_group.add_argument(
            '-f', '--final', action='store_true',
            help='Output a final summary of the project')

    def handle(self, *args, **options):
        if not self.verify_options(options):
            return

        if options['new']:
            project_id = self.create_project()
            self.project_info(project_id)

        elif options['status']:
            self.project_info(options['project_id'])

        elif options['final']:
            project_id = options['project_id']
            p_info = self.project_info(project_id, verbose=False)
            try:
                tasks = p_info[project_id]['tasks']
                assert tasks['copy_editing']['status'] == 'Complete'
                pprint(tasks['copy_editing']['latest_data'])
            except Exception:
                print("The '--final' option must be used with a completed "
                      "project")

    def create_project(self):
        project_id = create_orchestra_project(
            None,
            'journalism',
            'v1',
            'A test run of our journalism workflow',
            10,
            {
                'article_draft_template': '1F9ULJ_eoJFz1whqjK2thsC6gJup2f35IsUUpbcizcfA'  # noqa
            },
            'train',
        )
        print('Project with id {} created!'.format(project_id))
        return project_id

    def project_info(self, project_id, verbose=True):
        p_info = get_project_information([project_id])
        if verbose:
            print("Information received! Here's what we got:")
            print('')
            pprint(p_info)
        return p_info

    def verify_options(self, options):
        if options['new'] and options['project_id']:
            print("The '--new' option cannot be used in conjunction with a "
                  "project id.")
            return False

        elif options['status'] and not options['project_id']:
            print("The '--status' option must be used in conjunction with a "
                  "project id.")
            return False

        elif options['final'] and not options['project_id']:
            print("The '--final' option must be used in conjunction with a "
                  "project id.")
            return False
        return True
