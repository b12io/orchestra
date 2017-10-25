from django.core.management.base import BaseCommand

from orchestra.workflow.certifications import migrate_certifications


class Command(BaseCommand):
    help = 'Migrates specified certifications across workflows.'

    def add_arguments(self, parser):
        parser.add_argument(
            'source_workflow_slug',
            help='Slug for the source workflow from which to migrate '
                 'certifications.')
        parser.add_argument(
            'destination_workflow_slug',
            help='Slug for the destination workflow to which certifications '
                 'will be migrated.')
        parser.add_argument(
            '--certifications',
            nargs='+',
            metavar=('slug1', 'slug2'),
            help=('Certification slugs to migrate. If not specified, '
                  'migration of all certifications will be attempted.'))

    def handle(self, *args, **options):
        migrate_certifications(
            options['source_workflow_slug'],
            options['destination_workflow_slug'],
            options['certifications'])
