import logging
import re

from apiclient import errors
from apiclient.discovery import build
from apiclient.http import MediaFileUpload
from httplib2 import Http
from oauth2client.service_account import ServiceAccountCredentials

logger = logging.getLogger(__name__)
_image_mimetype_regex = re.compile('(image/(?:jpg|jpeg|gif|png))',
                                   re.IGNORECASE)


class Service(object):

    def __init__(self, google_p12_path, google_service_email):
        self._service = self._create_drive_service(google_p12_path,
                                                   google_service_email)

    def _create_drive_service(self, google_p12_path,
                              google_service_email):
        credentials = ServiceAccountCredentials.from_p12_keyfile(
            google_service_email,
            google_p12_path,
            scopes=['https://www.googleapis.com/auth/drive'])
        http_auth = credentials.authorize(Http())
        return build('drive', 'v2', http=http_auth, cache_discovery=False)

    def insert_file(self, title, description, parent_id, mime_type, filename):
        """Insert new file.

        Args:
          service: Drive API service instance.
          title: Title of the file to insert, including the extension.
          description: Description of the file to insert.
          parent_id: Parent folder's ID.
          mime_type: MIME type of the file to insert.
          filename: Filename of the file to insert.
        Returns:
          Inserted file metadata if successful, None otherwise.
        """
        media_body = MediaFileUpload(filename, mimetype=mime_type,
                                     resumable=True)

        body = {
            'title': title,
            'description': description,
            'mimeType': mime_type
        }

        # Set the parent folder.
        if parent_id:
            body['parents'] = [{'id': parent_id}]

        try:
            file = self._service.files().insert(
                body=body,
                media_body=media_body).execute()
            return file
        except errors.HttpError:
            logger.exception('An error while creating a file.')
            return None

    def copy_file(self, origin_file_id, copy_title, parent_ids=None):
        """
        Copy an existing file.
        """
        body = {'title': copy_title}
        if parent_ids is not None:
            body.update({'parents': [{'id': parent} for parent in parent_ids]})
        try:
            return self._service.files().copy(fileId=origin_file_id,
                                              body=body).execute()
        except errors.HttpError:
            logger.exception('An error occurred while copying file')
            return None

    def insert_folder(self, title, parent_id):
        """Insert new folder.

        Args:
          service: Drive API service instance.
          title: Title of the folder to insert, including the extension.
          parent_id: Parent folder id
          permissions: List of permissions
        Returns:
          Inserted file metadata if successful, None otherwise.
        """
        body = {
            'title': title,
            'mimeType': 'application/vnd.google-apps.folder'
        }

        # Set the parent folder.
        if parent_id:
            body['parents'] = [{'id': parent_id}]

        try:
            folder = self._service.files().insert(
                body=body).execute()
            return folder
        except errors.HttpError:
            logger.exception('An error while creating a folder.')
            return None

    def add_permission(self, file_id, permission):
        """
        Add permission of a certain type to a given file.
        """
        try:
            return (self._service.permissions()
                    .insert(fileId=file_id, body=permission)
                    .execute())
        except errors.HttpError as error:
            logger.exception('An error occured: %s', error)
            return None

    def delete_folder(self, folder_id):
        """
        Delete folder from a google drive.
        """
        try:
            return (self._service.files()
                    .delete(fileId=folder_id).execute())
        except errors.HttpError as error:
            logger.exception('An error occured: %s', error)
            return None

    def list_folder(self, folder_id):
        """Retrieve a list of File resources.

        Args:
            folder_id: ID of parent folder to list.
        Returns:
            List of File resources.
        """
        service = self._service
        result = []
        page_token = None
        while True:
            try:
                param = {
                    'q': "'{}' in parents".format(folder_id),
                }
                if page_token:
                    param['pageToken'] = page_token
                files = service.files().list(**param).execute()

                result.extend(files['items'])
                page_token = files.get('nextPageToken')
                if not page_token:
                    break
            except errors.HttpError as error:
                logger.exception('An error occurred: %s', error)
                return None
        return result

    def get_file_content(self, file_id):
        """Get a file's content.

        Args:
            file_id: ID of the file to get.

        Returns:
            File's content if successful, None otherwise.
        """
        try:
            return self._service.files().get_media(fileId=file_id).execute()
        except errors.HttpError as error:
            logger.exception('An error occurred: %s', error)
            return None
