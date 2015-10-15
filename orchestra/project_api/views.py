
import json

from django.core.urlresolvers import reverse
from jsonview.exceptions import BadRequest
from orchestra.models import Project
from orchestra.models import WorkerCertification
from orchestra.project import create_project_with_tasks
from orchestra.project_api.api import get_project_information
from orchestra.project_api.decorators import api_endpoint
from orchestra.workflow import get_workflows
from urllib.parse import urlparse
from urllib.parse import urlunsplit

import logging
logger = logging.getLogger(__name__)


@api_endpoint(['POST'])
def project_information(request):
    try:
        # TODO(marcua): Add checking for json.loads exceptions to all
        # endpoints.
        return get_project_information(
            json.loads(request.body.decode())['project_id'])
    except KeyError:
        raise BadRequest('project_id is required')
    except Project.DoesNotExist:
        raise BadRequest('No project for given id')


@api_endpoint(['POST'])
def create_project(request):
    project_details = json.loads(request.body.decode())
    try:
        if project_details['task_class'] == 'real':
            task_class = WorkerCertification.TaskClass.REAL
        else:
            task_class = WorkerCertification.TaskClass.TRAINING
        args = (
            project_details['workflow_slug'],
            project_details['description'],
            project_details['priority'],
            task_class,
            project_details['project_data'],
            project_details['review_document_url']
        )
    except KeyError:
        raise BadRequest('One of the parameters is missing')

    project = create_project_with_tasks(*args)
    return {'project_id': project.id}


@api_endpoint(['POST'])
def project_details_url(request):
    project_details = json.loads(request.body.decode())
    project_id = project_details.get('project_id')

    if project_id is None:
        raise BadRequest('project_id parameter is missing')
    project_details_url = reverse('orchestra:project_details',
                                  kwargs={'project_id':
                                          project_id})
    parsed_url = urlparse(request.build_absolute_uri())
    url = urlunsplit((parsed_url.scheme,
                      parsed_url.netloc,
                      project_details_url,
                      '',
                      ''))
    return {'project_details_url': url}


@api_endpoint(['GET'])
def workflow_types(request):
    workflows = get_workflows()
    workflow_choices = {workflow_slug: workflow.name for
                        workflow_slug, workflow in workflows.items()}
    return {'workflows': workflow_choices}
