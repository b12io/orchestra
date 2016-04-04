from setuptools import setup, find_packages

from release import get_version

version = get_version('orchestra')
setup(
    name='orchestra',
    version=version,
    description='A framework for building complex expert workflows.',
    author='Unlimited Labs, Inc.',
    author_email='hello@unlimitedlabs.com',
    license='Apache 2',
    url='https://github.com/unlimitedlabs/orchestra',
    download_url=(
        'https://github.com/unlimitedlabs/orchestra/tarball/v' + version),
    keywords=['crowdsourcing', 'workflows'],
    classifiers=[],
    packages=find_packages(),
    include_package_data=True,
)
