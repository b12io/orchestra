from setuptools import find_packages
from setuptools import setup

from release import get_version

version = get_version('orchestra')
setup(
    name='orchestra',
    version=version,
    description='A framework for building complex expert workflows.',
    author='B12 (Unlimited Labs, Inc.)',
    author_email='hello@b12.io',
    license='Apache 2',
    url='https://github.com/b12io/orchestra',
    download_url=(
        'https://github.com/b12io/orchestra/tarball/v' + version),
    keywords=['crowdsourcing', 'workflows'],
    classifiers=[],
    packages=find_packages(),
    include_package_data=True,
)
