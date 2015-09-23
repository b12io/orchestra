from unittest.mock import patch
from unittest.mock import MagicMock

from django.test import override_settings
from django.test import TestCase
from django.conf import settings

from orchestra.google_apps.convenience import _get_image_mimetype
from orchestra.google_apps.convenience import create_document_from_template
from orchestra.google_apps.convenience import create_folder_with_permissions
from orchestra.google_apps.convenience import create_media_folder_with_images
from orchestra.google_apps.convenience import Service
from orchestra.google_apps.convenience import add_image
from orchestra.google_apps.errors import InvalidUrlError
from orchestra.google_apps.errors import GoogleDriveError
from orchestra.tests.helpers.google_apps import mock_create_drive_service
from orchestra.tests.helpers.google_apps import fake_image_get


@override_settings(GOOGLE_APPS=True)
class TestGoogleAppsConvenience(TestCase):

    def setUp(self):
        super(TestGoogleAppsConvenience, self).setUp()

    def test_get_image_mimetype(self):
        # Content type is not provided.
        url = 'http://nocontenttype.com/image.jpeg'
        response = fake_image_get(url)
        mimetype = _get_image_mimetype(response, url)
        self.assertEquals(mimetype, 'image/jpeg')

        # Content type is provided.
        url = 'http://contenttype.com/image.jpg'
        response = fake_image_get(url)
        mimetype = _get_image_mimetype(response, url)
        self.assertEquals(mimetype, 'image/jpg')

    @patch('requests.get', side_effect=fake_image_get)
    @patch.object(Service, '_create_drive_service',
                  new=mock_create_drive_service)
    def test_add_image(self, requests_get):
        # Make sure if incorrect url then image is not returned.
        with self.assertRaises(InvalidUrlError):
            add_image(MagicMock(), 'test_folder', 'http://in.gogo/test.jp')

        service = Service(settings.GOOGLE_P12_PATH,
                          settings.GOOGLE_SERVICE_EMAIL)
        image_data = add_image(service, 'test_folder',
                               'http://nocontenttype.com/image.jpeg')
        self.assertEquals(image_data, {'id': 1})

        image_data = add_image(service, 'test_folder',
                               'http://nocontenttype.com/error.jpg')
        self.assertIsNone(image_data)

    @patch('requests.get', side_effect=fake_image_get)
    @patch.object(Service, '_create_drive_service',
                  new=mock_create_drive_service)
    def test_create_media_folder(self, requests_get):
        with self.assertRaises(GoogleDriveError):
            create_media_folder_with_images('test_parent_id',
                                            ['http://in.gogo/image.jpg'],
                                            'error')

        # Make sure that if the correct image is provided,
        # it creates a folder.
        media_images = create_media_folder_with_images(
            'test_parent_id',
            ['http://inp.gogo/image.jpg'],
            'test')
        self.assertEquals(media_images['folder']['id'], 1)
        self.assertEquals(
            media_images['image_counter']['uploaded_images'], 1)

        # Make sure that if the incorrect image is provided,
        # still returns a new folder.
        media_images = create_media_folder_with_images(
            'test_parent_id',
            ['http://nocontenttype.com/test.jp', None],
            'test')
        self.assertEquals(media_images['folder']['id'], 1)
        self.assertEquals(
            media_images['image_counter']['not_uploaded_images'], 2)

        with self.assertRaises(GoogleDriveError):
            folder = create_folder_with_permissions(
                'test_parent_id', 'error')

        # In order to test permission failure we did something convoluted.
        # create_folder_with_permissions calls service.insert_folder which in
        # turn will create a new folder named 'error'.
        # When we try to add permission to folder 'error' that fails in
        # our helper function and raises an error.
        folder = create_folder_with_permissions('test_parent_id',
                                                'permission_fail')
        self.assertEquals(folder['id'], 'error')

    @patch.object(Service, '_create_drive_service',
                  new=mock_create_drive_service)
    def test_delete_folder(self):
        service = Service(settings.GOOGLE_P12_PATH,
                          settings.GOOGLE_SERVICE_EMAIL)
        folder = service.delete_folder('test')
        self.assertEquals(folder['id'], 1)

        folder = service.delete_folder('error')
        self.assertIsNone(folder)

    @patch.object(Service, '_create_drive_service',
                  new=mock_create_drive_service)
    def test_create_document_from_template(self):
        upload_info = create_document_from_template('test_id', 'test_filename')
        self.assertEquals(upload_info['id'], 1)
        with self.assertRaises(GoogleDriveError):
            create_document_from_template('error', 'test_filename')
