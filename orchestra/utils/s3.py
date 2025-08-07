import os
from uuid import uuid1

import boto3
from django.conf import settings

from orchestra.core.errors import S3UploadError

# TODO(marcua): move into settings.py.
MAX_UPLOAD_SIZE_MB = 20


def upload_editor_image(image_data, image_type, prefix=None):
    """
    Upload image from rich text editor to the corresponding bucket.
    Returns public URL to the image.
    """
    image_extensions = {
        'image/jpeg': 'jpg',
        'image/png': 'png',
        'image/gif': 'gif',
    }

    try:
        extension = image_extensions[image_type]
    except KeyError:
        raise S3UploadError('File type {} not supported.'.format(image_type))

    return upload_file(settings.EDITOR_IMAGE_BUCKET_NAME,
                       image_data,
                       image_type,
                       extension,
                       acl_string='public-read',
                       prefix=prefix)


def upload_file(bucket_name, data, mime_type, extension,
                acl_string=None, prefix=None):
    """
    Upload file to provided s3 bucket and set file properties and permission.
    Returns a URL to the file.
    """
    s3_client = boto3.client('s3', aws_access_key_id=settings.AWS_S3_KEY, aws_secret_access_key=settings.AWS_S3_SECRET)

    s3_file_name = '{}.{}'.format(uuid1().hex, extension)
    if len(data) > MAX_UPLOAD_SIZE_MB * 10 ** 6:
        raise S3UploadError('File larger than {}MB max upload size.'
                            .format(MAX_UPLOAD_SIZE_MB))

    if prefix is not None:
        s3_file_name = os.path.join(prefix, s3_file_name)
    
    extra_args = {'ContentType': mime_type}
    if acl_string is not None:
        extra_args['ACL'] = acl_string
    
    s3_client.put_object(
        Bucket=bucket_name,
        Key=s3_file_name,
        Body=data,
        **extra_args
    )
    
    return f"https://{bucket_name}.s3.amazonaws.com/{s3_file_name}"
