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

logger = logging.getLogger(__name__)

_httpsig_auth = HTTPSignatureAuth(key_id=settings.ORCHESTRA_PROJECT_API_KEY,
                                  secret=settings.ORCHESTRA_PROJECT_API_SECRET,
                                  algorithm='hmac-sha256')
_api_root_url = '{}/orchestra/api/project/'.format(settings.ORCHESTRA_URL)


class OrchestraError(Exception):
    pass


def _make_api_request(method, endpoint, *args, **kwargs):
    func = getattr(requests, method)
    # Adding 'date' header as per
    # https://github.com/zzsnzmn/py-http-signature/blob/e2e2c753db7da45fab4b215d84e8d490bd708833/http_signature/sign.py#L155  # noqa
    headers = {'date': format_date_time(mktime(datetime.now().timetuple())),
               'X-Api-Version': '~6.5',
               'X-Api-Key': settings.ORCHESTRA_PROJECT_API_KEY}
    headers.update(kwargs.pop('headers', {}))
    all_kwargs = {'auth': _httpsig_auth, 'headers': headers}
    all_kwargs.update(kwargs)
    url = '{}{}/'.format(_api_root_url, endpoint)
    response = func(url, *args, **all_kwargs)
    if response.status_code != 200:
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


def get_project_information(project_id):
    data = {
        'project_id': project_id
    }
    response = _make_api_request('post', 'project_information',
                                 data=json.dumps(data))
    return json.loads(response.text)


def assign_worker_to_task(worker_id, task_id):
    data = {
        'worker_id': worker_id,
        'task_id': task_id,
    }
    response = _make_api_request('post', 'assign_worker_to_task',
                                 data=json.dumps(data))
    return json.loads(response.text)
