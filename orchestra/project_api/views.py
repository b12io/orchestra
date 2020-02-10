import logging
from urllib.parse import urlparse
from urllib.parse import urlunsplit

from django.urls import reverse
from jsonview.exceptions import BadRequest

from orchestra.core.errors import TaskAssignmentError
from orchestra.core.errors import WorkerCertificationError
from orchestra.models import Project
from orchestra.models import WorkerCertification
from orchestra.models import Workflow
from orchestra.project import create_project_with_tasks
from orchestra.project_api.api import get_project_information
from orchestra.utils.decorators import api_endpoint
from orchestra.utils.load_json import load_encoded_json
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.notifications import message_experts_slack_group
from orchestra.project_api.auth import OrchestraProjectAPIAuthentication
from orchestra.project_api.auth import IsSignedUser

logger = logging.getLogger(__name__)


@api_endpoint(methods=['POST'],
              permissions=(IsSignedUser,),
              logger=logger,
              auths=(OrchestraProjectAPIAuthentication,))
def project_information(request):
    try:
        data = load_encoded_json(request.body)
        project_ids = data['project_ids']
        return get_project_information(project_ids)
    except KeyError:
        raise BadRequest('project_ids is required')


@api_endpoint(methods=['POST'],
              permissions=(IsSignedUser,),
              logger=logger,
              auths=(OrchestraProjectAPIAuthentication,))
def create_project(request):
    project_details = load_encoded_json(request.body)
    try:
        if project_details['task_class'] == 'real':
            task_class = WorkerCertification.TaskClass.REAL
        else:
            task_class = WorkerCertification.TaskClass.TRAINING
        args = (
            project_details['workflow_slug'],
            project_details['workflow_version_slug'],
            project_details['description'],
            project_details['priority'],
            task_class,
            project_details['project_data'],
        )
    except KeyError:
        raise BadRequest('One of the parameters is missing')

    project = create_project_with_tasks(*args)
    return {'project_id': project.id}


@api_endpoint(methods=['POST'],
              permissions=(IsSignedUser,),
              logger=logger,
              auths=(OrchestraProjectAPIAuthentication,))
def project_details_url(request):
    project_details = load_encoded_json(request.body)
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


@api_endpoint(methods=['GET'],
              permissions=(IsSignedUser,),
              logger=logger,
              auths=(OrchestraProjectAPIAuthentication,))
def workflow_types(request):
    workflows = {
        w.slug: {
            'name': w.name,
            'versions': {
                v.slug: {
                    'name': v.name,
                    'description': v.description
                }
                for v in w.versions.all()
            }
        }
        for w in Workflow.objects.all()
    }
    return {'workflows': workflows}


@api_endpoint(methods=['POST'],
              permissions=(IsSignedUser,),
              logger=logger,
              auths=(OrchestraProjectAPIAuthentication,))
def assign_worker_to_task(request):
    data = load_encoded_json(request.body)
    errors = {}
    try:
        assign_task(data.get('worker_id'), data.get('task_id'))
    except WorkerCertificationError as e:
        errors['worker_certification_error'] = str(e)
    except TaskAssignmentError as e:
        errors['task_assignment_error'] = str(e)
    except Exception as e:
        errors['error'] = str(e)
    success = len(errors) == 0
    return {
        'success': success,
        'errors': errors,
    }


@api_endpoint(methods=['POST'],
              permissions=(IsSignedUser,),
              logger=logger,
              auths=(OrchestraProjectAPIAuthentication,))
def message_project_team(request):
    """
    Endpoint for sending arbitrary message to a project team.
    Payload example:
    {'message': 'Chat message', 'project_id': 'some-id-123'}
    """
    data = load_encoded_json(request.body)
    try:
        message = data['message']
        project_id = data['project_id']
        project = Project.objects.get(id=project_id)
    except KeyError:
        text = ('An object with `message` and `project_id` attributes'
                ' should be supplied')
        raise BadRequest(text)
    except Project.DoesNotExist:
        raise BadRequest('No project for given id')
    if project.slack_group_id:
        message_experts_slack_group(project.slack_group_id, message)
    else:
        error_message = (
            "The following project doesn't have slack_group_id: {}"
        ).format(project)
        raise BadRequest(error_message)
    return {'success': True}
