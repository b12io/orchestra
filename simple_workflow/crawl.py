from bs4 import BeautifulSoup
from urllib.parse import urljoin
from urllib.parse import urlparse

import logging
import random
import re
import requests

logger = logging.getLogger(__name__)

IMAGE_FILE_REGEX = re.compile('([-\w]+\.(?:jpg|jpeg|gif|png))',
                              re.IGNORECASE)


def crawl_page(project_data, prerequisites):
    """ Picks a random image off of the passed URL."""

    result = {
        'status': 'success',
        'image': None
    }
    url = project_data.get('url')
    if not url:
        result['status'] = 'error'
        result['error_message'] = 'URL was not provided.'
        return result

    # Crawl the website for images.
    logger.info('Starting to crawl %s', url)
    images = find_images(url)
    num_images = len(images)
    logger.info('Found %s images', num_images)
    if num_images == 0:
        result['status'] = 'error'
        result['error_message'] = 'Unable to find images at the provided URL.'
        return result

    # Return a random one.
    logger.info('Picking a random one...')
    image = random.choice(list(images))
    result['image'] = image
    return result


def find_images(url):
    """ Fetches a url's HTML and extracts all image sources in an <img> tag.
    """

    images = set()

    # Fetch the content.
    headers = {
        'User-Agent': ('Mozilla/5.0 (compatible; OrchestraBot/1.0; '
                       'noreply@example.org)'),
    }
    response = requests.get(url, headers=headers)
    if response.status_code < 200 or response.status_code >= 300:
        logger.error("Couldn't fetch url {}".format(url))
        return images
    content = response.text

    # Find images in the content.
    soup = BeautifulSoup(content)
    tags = soup.find_all('img', src=IMAGE_FILE_REGEX)
    for tag in tags:
        link = tag.get('src')
        if link is None:
            continue
        if not bool(urlparse(link).netloc):
            link = urljoin(url, link)
        images.add(link)
    return images
