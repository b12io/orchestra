import os
import tempfile

from django.conf import settings
from PIL import Image

from orchestra.google_apps.convenience import create_folder_with_permissions
from orchestra.google_apps.convenience import download_file
from orchestra.google_apps.convenience import upload_file
from orchestra.google_apps.permissions import write_with_link_permission
from orchestra.google_apps.service import Service

import logging
logger = logging.getLogger(__name__)


def autoadjust_photos(project_data, prerequisites):
    """Resize all images in a google drive directory."""
    task_data = {}
    parent_folder_id = project_data['project_folder_id']

    # Create a directory to output the photos
    output_folder = create_folder_with_permissions(
        parent_folder_id,
        'Processed Photos',
        permissions=[write_with_link_permission],
    )
    task_data['processed_photo_folder'] = output_folder['id']

    # List the existing photos
    raw_photo_folder_id = (prerequisites
                           .get('photography')
                           .get('prerequisites')
                           .get('article_planning')
                           .get('prerequisites')
                           .get('document_creation')
                           .get('task')
                           .get('data')
                           .get('raw_photo_folder'))
    service = Service(settings.GOOGLE_P12_PATH,
                      settings.GOOGLE_SERVICE_EMAIL)
    photos_metadata = service.list_folder(raw_photo_folder_id)

    # Iterate over the input photos and process them.
    task_data['photos_for_caption'] = []
    for photo_metadata in photos_metadata:
        photo, title, mimetype = download_file(photo_metadata)
        adjusted_photo_tmpfile = adjust_photo(photo)
        upload = upload_file(
            task_data['processed_photo_folder'],
            adjusted_photo_tmpfile.name,
            title,
            'image',
            mimetype
        )
        os.unlink(adjusted_photo_tmpfile.name)
        embed_link = upload['webContentLink'].replace('&export=download', '')
        task_data['photos_for_caption'].append(embed_link)
    return task_data


def adjust_photo(photo):

    # Write the photo to a temporary file
    temp = tempfile.NamedTemporaryFile(mode='wb', delete=False)
    temp.write(photo)

    # Open it up and play with it in PIL
    im = Image.open(temp.name)
    im = im.convert('L')  # convert to greyscale

    # Save it back out into a new temporary file
    os.unlink(temp.name)
    temp2 = tempfile.NamedTemporaryFile(mode='wb', delete=False)
    im.save(temp2, format='jpeg')
    return temp2
