import json

from base64 import b64decode
from beanstalk_dispatch.execution import execute_function
from jsonview.decorators import json_view
from jsonview.exceptions import BadRequest
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

import logging
logger = logging.getLogger(__name__)


@require_http_methods(['POST'])
@json_view
@csrf_exempt
def dispatcher(request):
    function_request = json.loads(b64decode(request.body.decode()).decode())
    try:
        execute_function(function_request)
        return {}
    except Exception as e:
        logger.error('Failure running function', exc_info=True)
        raise BadRequest(e)
