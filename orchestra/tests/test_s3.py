import math
from unittest.mock import patch

from django.test import TestCase

from orchestra.core.errors import S3UploadError
from orchestra.utils.s3 import upload_editor_image
from orchestra.utils.s3 import MAX_UPLOAD_SIZE_MB


@patch('orchestra.utils.s3.boto')
class BasicS3TestCase(TestCase):
    def test_upload_editor_image(self, boto_patch):
        # Sample unicode data string
        sample_data = 'data'.encode()

        # Attempt to upload incorrect image type
        with self.assertRaises(S3UploadError):
            upload_editor_image(sample_data, 'invalid_type')

        # Upload supported image type
        upload_editor_image(sample_data, 'image/jpeg')

        max_size_bytes = MAX_UPLOAD_SIZE_MB * 10 ** 6

        # Attempt to upload image larger than size limit
        sample_data = ('a' * math.floor(max_size_bytes * 1.0001)).encode()
        with self.assertRaises(S3UploadError):
            upload_editor_image(sample_data, 'image/jpeg')

        # Upload image smaller than size limit
        sample_data = ('a' * math.floor(max_size_bytes * 0.9999)).encode()
        upload_editor_image(sample_data, 'image/jpeg')
