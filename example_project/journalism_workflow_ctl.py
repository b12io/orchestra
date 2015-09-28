from pprint import pprint

import argparse
import os
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


def main(args):
    if args.new:
        project_id = create_project()
        project_info(project_id)
        return

    elif args.status:
        project_info(args.project_id)

    elif args.final:
        p_info = project_info(args.project_id, verbose=False)
        try:
            assert p_info['tasks']['copy_editing']['status'] == 'Complete'
            pprint(p_info['tasks']['copy_editing']['latest_data'])
        except Exception:
            print("The '--final' option must be used with a completed project")
            sys.exit()


def create_project():
    project_id = create_orchestra_project(
        None,
        'journalism',
        'A test run of our journalism workflow',
        10,
        {
            'article_draft_template': '1F9ULJ_eoJFz1whqjK2thsC6gJup2f35IsUUpbcizcfA'  # noqa
        },
        'https://docs.google.com/document/d/1s0IJycNAwHtZfsUwyo6lCJ7kI9pTOZddcaiRDdZUSAs',  # noqa
        'train',
    )
    print('Project with id {} created!'.format(project_id))
    return project_id


def project_info(project_id, verbose=True):
    p_info = get_project_information(project_id)
    if verbose:
        print("Information received! Here's what we got:")
        print('')
        pprint(p_info)
    return p_info


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-p', '--project-id',
                        help='Existing project id to check status of')
    primary_command_group = parser.add_mutually_exclusive_group(required=True)
    primary_command_group.add_argument('-n', '--new', action='store_true',
                                       help='Start a new journalism project')
    primary_command_group.add_argument('-s', '--status', action='store_true',
                                       help=('Check the status of an '
                                             'in-progress project'))
    primary_command_group.add_argument('-f', '--final', action='store_true',
                                       help=('Output a final summary of the '
                                             'project'))
    args = parser.parse_args()

    if args.new and args.project_id:
        print("The '--new' option cannot be used in conjunction with a "
              "project id.")
        sys.exit()
    elif args.status and not args.project_id:
        print("The '--status' option must be used in conjunction with a "
              "project id.")
        sys.exit()
    elif args.final and not args.project_id:
        print("The '--final' option must be used in conjunction with a "
              "project id.")
        sys.exit()

    main(args)
