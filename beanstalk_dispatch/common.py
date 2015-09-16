import json

from beanstalk_dispatch import ARGS
from beanstalk_dispatch import FUNCTION
from beanstalk_dispatch import KWARGS


def create_request_body(function_name, *args, **kwargs):
    return json.dumps({FUNCTION: function_name, ARGS: args, KWARGS: kwargs})
