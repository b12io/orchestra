import logging
import os
import re
import tempfile
from collections import Counter
from datetime import date

import requests
from django.conf import settings

from orchestra.google_apps.errors import FailedRequest
from orchestra.google_apps.errors import GoogleDriveError
from orchestra.google_apps.errors import InvalidUrlError
from orchestra.google_apps.permissions import read_with_link_permission
from orchestra.google_apps.permissions import write_with_link_permission
from orchestra.google_apps.service import Service
from orchestra.utils.common_regex import image_file_regex
from orchestra.utils.decorators import run_if

logger = logging.getLogger(__name__)
_image_mimetype_regex = re.compile('(image/(?:jpg|jpeg|gif|png|svg))',
                                   re.IGNORECASE)
TEAM_MESSAGES_TEMPLATE_ID = '1d0kIgq8G_Su6j5abP-tP6yJ2sp-sFDk6vZiREil0_70'


def _get_image_mimetype(response, title):
    """
    Provided http response and an image title
    generate an image mimetype.
    """
    if (response.headers.get('content-type') and
        _image_mimetype_regex.search(response.headers
                                     .get('content-type'))):
        return response.headers.get('content-type')
    extension = title.split('.')[-1]
    return 'image/{}'.format(extension)


@run_if('GOOGLE_APPS')
def add_image(service, folder_id, url):
    """
    Add image to a folder.

    Args:
      service: Drive API service instance.
      folder_id: ID of a folder where the image will be stored
      url: url to the original image

    Returns:
      Metadata to an uploaded file
    """

    response = requests.get(url, stream=True)
    if response.status_code != 200:
        raise FailedRequest('Unable to successfully retrieve '
                            'an image: %s', (url))

    temp = tempfile.NamedTemporaryFile(mode='wb', delete=False)
    for chunk in response.iter_content(1024):
        temp.write(chunk)

    title_regex = image_file_regex.search(response.url)
    if title_regex is None:
        raise InvalidUrlError('Url is not for an image.')

    title = title_regex.group()
    mimetype = _get_image_mimetype(response, title)
    temp.close()
    google_image = service.insert_file(title,
                                       'image',
                                       folder_id,
                                       mimetype,
                                       temp.name)
    os.unlink(temp.name)
    return google_image


@run_if('GOOGLE_APPS')
def create_media_folder_with_images(parent_id, image_links, folder_name):
    """
    Given a folder name and a list of image links create a new
    google drive folder with images in it.
    """
    service = Service(settings.GOOGLE_P12_PATH,
                      settings.GOOGLE_SERVICE_EMAIL)
    folder = create_folder_with_permissions(parent_id,
                                            folder_name,
                                            [read_with_link_permission])
    folder_id = folder['id']
    counter = Counter()
    for image_link in image_links:
        try:
            image = add_image(service, folder_id, image_link)
            counter['uploaded_images'] += 1
            logger.info('Image has been uploaded %s', image)
        except (InvalidUrlError, FailedRequest):
            counter['not_uploaded_images'] += 1
            logger.exception('Failed to retrieve image from %s',
                             image_link)
    return {'folder': folder,
            'image_counter': counter}


@run_if('GOOGLE_APPS')
def create_folder_with_permissions(parent_id, folder_name, permissions=None):
    """
    Create drive folder in the specified location with given permissions.
    """
    service = Service(settings.GOOGLE_P12_PATH,
                      settings.GOOGLE_SERVICE_EMAIL)
    folder = service.insert_folder(folder_name, parent_id)
    if folder is None:
        raise GoogleDriveError('Could not create a folder')

    permissions = permissions or []
    for permission in permissions:
        service.add_permission(folder.get('id'),
                               permission)

    return folder


@run_if('GOOGLE_APPS')
def create_project_google_folder(project):
    """
    Create drive folder for project information
    """
    today = date.today().strftime('%Y-%m-%d')
    parent_id = (project.project_data.get('client_folder_id') or
                 settings.GOOGLE_PROJECT_ROOT_ID)
    folder = create_folder_with_permissions(
        parent_id,
        ' '.join((today, project.short_description)),
        [write_with_link_permission])
    folder_id = folder.get('id')
    project.project_data['project_folder_id'] = folder_id
    project.team_messages_url = create_document_from_template(
        TEAM_MESSAGES_TEMPLATE_ID,
        'Team Messages',
        [folder_id],
        [write_with_link_permission])['alternateLink']
    project.save()
    return folder


@run_if('GOOGLE_APPS')
def create_document_from_template(template_id, name,
                                  parent_ids=None, permissions=None):
    service = Service(settings.GOOGLE_P12_PATH,
                      settings.GOOGLE_SERVICE_EMAIL)
    upload_info = service.copy_file(template_id, name,
                                    parent_ids=parent_ids)
    if upload_info is None:
        raise GoogleDriveError('Could not create document {}'.format(name))

    logger.info(upload_info)
    document_id = upload_info.get('id')

    permissions = permissions or []
    for permission in permissions:
        service.add_permission(document_id, permission)

    upload_info['status'] = 'success'
    upload_info['id'] = document_id
    return upload_info


@run_if('GOOGLE_APPS')
def download_file(file_metadata):
    """Download a file from a google drive folder.

    Args:
        file_metadata (dict):
            A Google Apps API file resource.

    Returns:
        file_contents (str):
            A buffer containing the raw binary contents of the file.
        title (str):
            The title of the file.
        mimetype(str):
            The mimetype of the file.
    """

    service = Service(settings.GOOGLE_P12_PATH,
                      settings.GOOGLE_SERVICE_EMAIL)
    mimetype = file_metadata['mimeType']
    title = file_metadata['title']
    return service.get_file_content(file_metadata['id']), title, mimetype


@run_if('GOOGLE_APPS')
def upload_file(parent_id, file_path, title, description, mimetype):
    """Upload a file to a google drive folder.

    Args:
        parent_id (str):
            Identifier for the drive folder to upload to.
        file_path (str):
            Local file path to the file to upload.
        title (str):
            Title for the uploaded document.
        description (str):
            A description of the file to upload.
        mimetype (str):
            Mimetype of the uploaded content.

    Returns:
        file_metadata (dict):
            A Google Apps File resource with metadata about the uploaded file.
    """

    service = Service(settings.GOOGLE_P12_PATH,
                      settings.GOOGLE_SERVICE_EMAIL)
    file_metadata = service.insert_file(
        title,
        description,
        parent_id,
        mimetype,
        file_path
    )
    return file_metadata
