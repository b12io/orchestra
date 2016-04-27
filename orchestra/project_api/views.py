import json
from urllib.parse import urlparse
from urllib.parse import urlunsplit

from django.core.urlresolvers import reverse
from jsonview.exceptions import BadRequest
from orchestra.models import Project
from orchestra.models import WorkerCertification
from orchestra.models import Workflow
from orchestra.project import create_project_with_tasks
from orchestra.project_api.api import get_project_information
from orchestra.project_api.decorators import api_endpoint
from orchestra.serializers import WorkflowSerializer

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
    for param in (
            'workflow_version', 'description', 'priority', 'project_data',
            'task_class'):
        if project_details.get(param) is None:
            raise BadRequest('Missing paramater {}'.format(param))
        if project_details['task_class'] == 'real':
            task_class = WorkerCertification.TaskClass.REAL
        else:
            task_class = WorkerCertification.TaskClass.TRAINING
    project = create_project_with_tasks(
        project_details['workflow_version'],
        project_details['description'],
        project_details['priority'],
        project_details['project_data'],
        task_class)
    return {'project_id': project.id}


@api_endpoint(['POST'])
def project_details_url(request):
    project_details = json.loads(request.body.decode())
    project_id = project_details.get('project_id')

    if project_id is None:
        raise BadRequest('project_id parameter is missing')
    project_details_url = '{}/project/{}'.format(
        reverse('orchestra:index'), project_id)
    parsed_url = urlparse(request.build_absolute_uri())
    url = urlunsplit((parsed_url.scheme,
                      parsed_url.netloc,
                      project_details_url,
                      '',
                      ''))
    return {'project_details_url': url}


@api_endpoint(['GET'])
def workflow_types(request):
    workflows = {
        w.slug: WorkflowSerializer(w).data
        for w in Workflow.objects.all()
    }
    return {'workflows': workflows}
