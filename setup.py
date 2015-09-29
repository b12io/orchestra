from setuptools import setup, find_packages
setup(
    name='orchestra',
    version='0.1.0',
    description='A framework for building complex expert workflows.',
    author='Unlimited Labs, Inc.',
    author_email='hello@unlimitedlabs.com',
    url='https://github.com/unlimitedlabs/orchestra',
    download_url=(
        'https://github.com/unlimitedlabs/orchestra/tarball/v0.1.0'),
    keywords=['crowdsourcing', 'workflows'],
    classifiers=[],
    packages=find_packages(),
    include_package_data=True,

)
