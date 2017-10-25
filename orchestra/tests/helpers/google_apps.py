from unittest.mock import MagicMock

from apiclient import errors


class FakeImageResponse(object):

    def __init__(self, url):
        self.url = url

        if url is None:
            self.status_code = 400
        else:
            self.status_code = 200

            if 'nocontenttype' not in url:
                self.headers = {
                    'content-type': 'image/jpg'
                }
            else:
                self.headers = {}

    def iter_content(self, size):
        return [b'chunk1']


def _execute_permission_fail():
    return {'id': 'error'}


def _execute_no_error():
    return {'id': 1, 'alternateLink': 'http://a.google.com/link'}


def _execute_error():
    raise errors.HttpError(resp='', content=b'')


def _insert_delete_copy(**kwargs):
    insert_obj = MagicMock()
    body = kwargs.get('body')
    if ((body and body.get('title') and 'error' in body['title']) or
            kwargs.get('fileId') == 'error'):
        insert_obj.execute = _execute_error
    elif (kwargs.get('body') and
          kwargs['body'].get('title') and
          'permission_fail' in kwargs['body']['title']):
        insert_obj.execute = _execute_permission_fail
    else:
        insert_obj.execute = _execute_no_error
    return insert_obj


def _files():
    files_obj = MagicMock()
    files_obj.insert = _insert_delete_copy
    files_obj.delete = _insert_delete_copy
    files_obj.copy = _insert_delete_copy
    return files_obj


_drive_service = MagicMock()
_drive_service.files = _files
_drive_service.permissions = _files
mock_create_drive_service = MagicMock(return_value=_drive_service)


def fake_image_get(url, *args, **kwargs):
    return FakeImageResponse(url)
