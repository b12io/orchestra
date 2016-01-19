from django.db import transaction

from orchestra.models import Certification
from orchestra.models import WorkerCertification
from orchestra.models import Workflow

import logging
logger = logging.getLogger(__name__)


@transaction.atomic
def migrate_certifications(source_workflow_slug,
                           destination_workflow_slug,
                           certification_slugs):
    source_worker_certifications = WorkerCertification.objects.filter(
        certification__workflow__slug=source_workflow_slug)

    source_workflow = Workflow.objects.get(slug=source_workflow_slug)
    source_certifications = source_workflow.certifications
    if certification_slugs:
        source_certifications = source_certifications.filter(
            slug__in=certification_slugs)
        not_found_certifications = set(certification_slugs) - set(list(
            source_certifications.values_list('slug', flat=True)))
        if not_found_certifications:
            logger.exception(
                "Certifications {} don't exist for the source workflow".format(
                    not_found_certifications))

    for source_certification in source_certifications.all():
        certification_slug = source_certification.slug
        logger.warning('Migrating {} certifications from {} to {}...'.format(
            certification_slug,
            source_workflow_slug,
            destination_workflow_slug))
        try:
            destination_certification = Certification.objects.get(
                workflow__slug=destination_workflow_slug,
                slug=certification_slug)
        except Certification.DoesNotExist:
            logger.exception(
                ("Certification {} doesn't exist for the destination workflow"
                    .format(certification_slug, destination_workflow_slug)))
            continue

        for worker_certification in source_worker_certifications.filter(
                certification=source_certification).order_by('role'):
            WorkerCertification.objects.get_or_create(
                certification=destination_certification,
                worker=worker_certification.worker,
                task_class=worker_certification.task_class,
                role=worker_certification.role)
