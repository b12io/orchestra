"""Increments the Orchestra version and pushes a new release to PyPI.

This script can only be called by orchestra core committers, and will result
in permission errors otherwise.
"""
import os
import re
import shutil
from argparse import ArgumentParser
from distutils.version import StrictVersion
from subprocess import check_output
from tempfile import mkdtemp

VERSION_RE = re.compile("__version__ = ['\"]([^'\"]+)['\"]")


def main(args):
    # Compute the new version number
    old_version = get_version('orchestra')
    new_version = increment_version_number(old_version, args.version_part)

    # Verify that our git setup is reasonable and print a loud warning.
    verify_and_warn(old_version, new_version, args)

    # Update orchestra/__init__.py with the new version
    if args.no_commit:
        print('--no-commit passed, not committing new version to Orchestra.')
        release_version = old_version
        version_text = 'current'
    else:
        update_version('orchestra', new_version, fake=args.fake)
        release_version = new_version
        version_text = 'new'

        # Commit the update to the repo
        commit_and_push(fake=args.fake)

    # Create a new tag for the release
    if args.no_tag:
        print('--no-tag passed, not tagging the {} version.'.format(
            version_text))
        tag_str = 'v{}'.format(release_version)
    else:
        tag_str = tag_release(release_version, fake=args.fake)

    # Release the new version on pypi
    if args.no_pypi:
        print('--no-pypi passed, not releasing the {} version to PyPI.'.format(
            version_text))
    else:
        pypi_release(tag_str, fake=args.fake)

    if not args.no_tag:
        print('Congratulations! Version {} has been tagged. You will want to '
              'make sure that the documentation is up to date, by activating '
              'v{} and by forcing a rebuild of the stable version. '
              .format(release_version, release_version))


def verify_and_warn(old_version, new_version, args):
    # verify that we're on the master branch
    branch_cmd = ['git', 'symbolic-ref', '--short', 'HEAD']
    cur_branch = run_command(branch_cmd).strip().lower()
    if cur_branch != 'master':
        print('This script must be run from the master branch. Exiting.')
        exit()

    # verify that master is up to date
    rev_cmd = ['git', 'rev-list']
    unpushed_cmd = rev_cmd + ['origin/master..']
    unpushed_commits = run_command(unpushed_cmd).strip()
    if unpushed_commits:
        print('Your branch has commits not yet on origin/master. Exiting.')
        exit()

    run_command(['git', 'fetch', 'origin', 'master'])
    unpulled_cmd = rev_cmd + ['..origin/master']
    unpulled_commits = run_command(unpulled_cmd).strip()
    if unpulled_commits:
        print('Your branch is behind origin/master. Exiting.')
        exit()

    # verify that there are no outstanding changes
    status_cmd = ['git', 'status', '--porcelain']
    status_output = run_command(status_cmd).strip()
    if status_output:
        print('There are outstanding changes to your branch. Exiting.')
        exit()

    action_text = get_action_text(old_version, new_version, args)
    if not action_text:  # Nothing to warn about.
        return
    print('WARNING: running this script will {}. This involves making changes '
          'you CANNOT TAKE BACK. Before proceeding, ensure that you are on '
          'the master branch, have pulled the latest changes, and have no '
          'outstanding local changes. THIS SCRIPT WILL FAIL if you do not '
          'have credentials to push to the Orchestra GitHub repository or the '
          'Orchestra PyPI account.'.format(action_text))
    ack = input('ARE YOU SURE YOU WISH TO PROCEED? (Type "release" to '
                'confirm): ').lower().strip('\' "')
    while ack in ['y', 'yes']:
        ack = input('Please type "release" to confirm: ')
    if ack != 'release':
        exit()


def get_action_text(old_version, new_version, args):
    actions = []
    release_version = old_version if args.no_commit else new_version
    if not args.no_commit:
        actions.append('increment the Orchestra version from {} to {}'.format(
            old_version, new_version))
    if not args.no_tag:
        actions.append('create a tag for version {}'.format(release_version))
    if not args.no_pypi:
        actions.append('release a PyPI distribution for version {}'.format(
            release_version))
    if not actions:
        return ''

    if len(actions) == 1:
        action_text = actions[0]
    elif len(actions) == 2:
        action_text = ' and '.join(actions)
    else:
        actions[-1] = 'and ' + actions[-1]
        action_text = ', '.join(actions)
    return action_text


def increment_version_number(old_version, version_part):
    version_parsed = StrictVersion(old_version)
    major, minor, patch = version_parsed.version
    if version_part == 'major':
        major += 1
        minor = 0
        patch = 0
    elif version_part == 'minor':
        minor += 1
        patch = 0
    elif version_part == 'patch':
        patch += 1
    new_version = '{}.{}.{}'.format(major, minor, patch)
    return new_version


def version_file(package):
    return os.path.join(package, '__init__.py')


def get_version(package):
    """ Return package version as listed in `__version__` in `init.py`."""
    # Parsing the file instead of importing it Pythonically allows us to make
    # this script completely Django-independent. This function is also used by
    # setup.py, which cannot import the package it is installing.
    with open(version_file(package), 'r') as f:
        init_py = f.read()
    return VERSION_RE.search(init_py).group(1)


def update_version(package, new_version, fake=False):
    # Update the __init__.py file with the new version.
    init_file = version_file(package)
    with open(init_file, 'r') as f:
        old_initpy = f.read()
    new_initpy = VERSION_RE.sub("__version__ = '{}'".format(new_version),
                                old_initpy)

    # Write the file out to disk.
    if fake:
        print('--fake passed, not updating {}'.format(init_file))
    else:
        print('Updating version in {}'.format(init_file))
        with open(version_file(package), 'w') as f:
            f.write(new_initpy)


def commit_and_push(fake=False):
    # commit all changes
    wrap_command(['git', 'commit', '-am', 'Version bump.'], fake)

    # Push changes
    wrap_command(['git', 'push', 'origin', 'master'], fake)


def tag_release(version, fake=False):
    # Create the tag
    tag_str = 'v{}'.format(version)
    tag_msg = 'Version {} of Orchestra'.format(version)
    tag_cmd = ['git', 'tag', '-am', tag_msg, tag_str]
    wrap_command(tag_cmd, fake)

    # Update the stable tag
    stable_tag_msg = 'The latest stable release of Orchestra.'
    stable_tag_cmd = ['git', 'tag', '-afm', stable_tag_msg, 'stable']
    wrap_command(stable_tag_cmd, fake)

    # Push the tags
    wrap_command(['git', 'push', '-f', '--tags'], fake)

    return tag_str


def pypi_release(tag_str, fake=False):
    # Create a temporary directory for the release
    release_dir = mkdtemp()
    print('Created release directory in {}'.format(release_dir))

    # Move into the release directory
    old_dir = os.getcwd()
    os.chdir(release_dir)

    # Clone the git repo for release
    print('Cloning Orchestra into the new release directory.')
    clone_cmd = ['git', 'clone', 'https://github.com/b12io/orchestra',
                 '-b', tag_str]
    wrap_command(clone_cmd, fake)  # This is safe to always run.
    if not fake:
        os.chdir('orchestra')

    # Release to pypi
    print('Releasing Orchestra to PyPI.')
    pypi_cmd = ['python3', 'setup.py', 'sdist', 'upload', '-r', 'pypi']
    wrap_command(pypi_cmd, fake)

    # Clean up
    print('Cleaning up release directory.')
    os.chdir(old_dir)
    shutil.rmtree(release_dir)


def wrap_command(cmd, fake):
    cmd_str = ' '.join(cmd)
    if fake:
        print('--fake passed, not running "{}"'.format(cmd_str))
        return ''
    print('Running command "{}"'.format(cmd_str))
    run_command(cmd)


def run_command(cmd):
    return check_output(cmd).decode()


def parse_args():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument(
        'version_part',
        choices=['major', 'minor', 'patch'],
        help=('The part of the version to increase: major (e.g., 1.0.0 => '
              '2.0.0), minor (e.g., 0.1.0 => 0.2.0), or patch (e.g., 0.0.1 => '
              '0.0.2).'))
    parser.add_argument(
        '--fake',
        action='store_true',
        help=('Fake the release without actually changing anything (useful '
              'for testing).'))
    parser.add_argument(
        '--no-commit',
        action='store_true',
        help=("Don\'t push a commit that updates the version number in the "
              "codebase (i.e., release the current version. Useful for "
              " continuing if the script ran partially before)."))
    parser.add_argument(
        '--no-tag',
        action='store_true',
        help=("Don\'t create a tag for the new version (i.e., release the "
              "current version's tag. Useful for continuing if the script ran "
              "partially before)."))
    parser.add_argument(
        '--no-pypi',
        action='store_true',
        help=("Don\'t create a new pypi release."))

    return parser.parse_args()


if __name__ == '__main__':
    main(parse_args())
