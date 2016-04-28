import json
import logging

logger = logging.getLogger(__name__)


def load_encoded_json(encoded_data):
    """
        Return a dictionary from a byte object encoded as json.
    """
    # TODO(joshblum): grep around the code base and use this function where we
    # can
    try:
        json_data = encoded_data.decode('utf-8')
        data = json.loads(json_data)
    except (AttributeError, ValueError, UnicodeError) as e:
        logger.warn('Json decode error {}'.format(str(e)))
        data = {}
    return data
