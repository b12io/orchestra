"""
This is the Orchestra Project Python API.

TODO(marcua): Move this file to its own pip/github project.
"""

import json
import logging
from datetime import datetime
from time import mktime
from wsgiref.handlers import format_date_time

import requests
from django.conf import settings
from httpsig.requests_auth import HTTPSignatureAuth
from orchestra.utils.convert_key_to_int import convert_key_to_int

logger = logging.getLogger(__name__)

_httpsig_auth = HTTPSignatureAuth(key_id=settings.ORCHESTRA_PROJECT_API_KEY,
                                  secret=settings.ORCHESTRA_PROJECT_API_SECRET,
                                  algorithm='hmac-sha256')
_api_root_url = '{}/orchestra/api/project/'.format(settings.ORCHESTRA_URL)


class OrchestraError(Exception):
    pass


def _make_api_request(method, endpoint, query_params='', *args, **kwargs):
    func = getattr(requests, method)
    # Adding 'date' header as per
    # https://github.com/zzsnzmn/py-http-signature/blob/e2e2c753db7da45fab4b215d84e8d490bd708833/http_signature/sign.py#L155  # noqa
    headers = {'date': format_date_time(mktime(datetime.now().timetuple())),
               'X-Api-Version': '~6.5',
               'X-Api-Key': settings.ORCHESTRA_PROJECT_API_KEY}
    headers.update(kwargs.pop('headers', {}))
    all_kwargs = {'auth': _httpsig_auth, 'headers': headers}
    all_kwargs.update(kwargs)
    url = '{}{}/{}'.format(_api_root_url, endpoint, query_params)
    response = func(url, *args, **all_kwargs)
    if response.status_code != 200 and response.status_code != 201:
        raise OrchestraError(response.text)
    return response


def get_workflow_types():
    response = _make_api_request('get', 'workflow_types')
    return json.loads(response.text)['workflows']


def get_project_details_url(project_id):
    data = {'project_id': project_id}
    response = _make_api_request('post', 'project_details_url',
                                 data=json.dumps(data))
    url = json.loads(response.text)['project_details_url']
    return url


def create_orchestra_project(client,
                             workflow_slug,
                             workflow_version_slug,
                             description,
                             priority,
                             project_data,
                             task_class):
    data = {
        'workflow_slug': workflow_slug,
        'workflow_version_slug': workflow_version_slug,
        'description': description,
        'priority': priority,
        'project_data': project_data,
        'task_class': task_class
    }
    response = _make_api_request('post', 'create_project',
                                 data=json.dumps(data))
    project_id = json.loads(response.text)['project_id']
    return project_id


def get_project_information(project_ids):
    data = {
        'project_ids': project_ids
    }
    response = _make_api_request('post', 'project_information',
                                 data=json.dumps(data))
    return json.loads(response.text, object_hook=convert_key_to_int)


def create_todos(todos):
    response = _make_api_request('post', 'todo-api',
                                 data=json.dumps(todos))
    return json.loads(response.text)


def get_todos(project_id, step_slug=None):
    if project_id is None:
        raise OrchestraError('project_id is required')
    project_param = 'project={}'.format(project_id)
    step_slug_param = '&step__slug={}'.format(
        step_slug) if step_slug is not None else ''
    query_params = '?{}{}'.format(project_param, step_slug_param)

    response = _make_api_request('get', 'todo-api', query_params)
    return json.loads(response.text)


def update_todos(updated_todos):
    response = _make_api_request('patch', 'todo-api',
                                 data=json.dumps(updated_todos))
    return json.loads(response.text)


def delete_todos(todo_ids):
    response = _make_api_request('delete', 'todo-api',
                                 data=json.dumps(todo_ids))
    return json.loads(response.text)


def assign_worker_to_task(worker_id, task_id):
    data = {
        'worker_id': worker_id,
        'task_id': task_id,
    }
    response = _make_api_request('post', 'assign_worker_to_task',
                                 data=json.dumps(data))
    return json.loads(response.text)


def message_project_team(project_id, message):
    data = {
        'project_id': project_id,
        'message': message
    }
    response = _make_api_request('post', 'message_project_team',
                                 data=json.dumps(data))
    return json.loads(response.text)
