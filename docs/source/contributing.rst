How to contribute to Orchestra
==============================

So you want to get involved in developing Orchestra. Great! We're excited to
have your support. This document lays down a few guidelines to help the whole
process run smoothly.

Getting involved
################

First, if you find a bug in the code or documentation, check out
our `open issues <https://github.com/unlimitedlabs/orchestra/issues>`_ and
`pull requests <https://github.com/unlimitedlabs/orchestra/pulls>`_ to see if
we're already aware of the problem. Also feel free to reach out to us on
`gitter <https://gitter.im/unlimitedlabs/orchestra>`_ to answer questions at
any time, or `subscribe to the Orchestra mailing list
<https://groups.google.com/forum/#!forum/orchestra-devel>`_ for longer
conversations.

If you've uncovered something new, please `create an issue
<https://github.com/unlimitedlabs/orchestra/issues>`_ describing the problem.
If you've written code that fixes an issue, `create a pull request
<https://help.github.com/articles/creating-a-pull-request/>`_ (PR) so it's easy
for us to incorporate your changes.

Development Workflow
####################

Github provides a nice `overview on how to create a pull request
<https://help.github.com/articles/creating-a-pull-request/>`_.

Some general rules to follow:

* Do your work in a `fork <https://help.github.com/articles/fork-a-repo/>`_
  of the Orchestra repo.

* Create a branch for each feature/bug in Orchestra that you're working on.
  These branches are often called "feature" or "topic" branches.

* Use your feature branch in the pull request. Any changes that you push to
  your feature branch will automatically be shown in the pull request.

* Keep your pull requests as small as possible. Large pull requests are hard to
  review. Try to break up your changes into self-contained and incremental pull
  requests, if need be, and reference dependent pull requests, e.g. "This pull
  request builds on request #92. Please review #92 first."

* Include unit tests with your pull request. We love tests and use `CircleCI
  <https://circleci.com/>`_ to check every pull request and commit.
  Check out our tests in ``orchestra/tests`` to see examples of how to write
  unit tests. Before submitting a PR, make sure that running ``make test`` from
  the root directory of the repository succeeds.

* Additionally, we try to maintain high `code coverage
  <https://en.wikipedia.org/wiki/Code_coverage>`_. To verify that your changes
  are well-covered by tests, run ``make test_coverage``, which will run the
  tests, then print out percent coverage for each file in Orchestra. Aim for
  100% for every new file you create!

* Once you submit a PR, you'll get feedback on your code, sometimes asking for
  a few rounds of changes before your PR is accepted. After each round of
  comments, make changes accordingly, then squash all changes for that round
  into a single commit with a name like 'changes round 0'.

* After your PR is accepted, you should squash all of your changes into a
  single commit before we can merge them into the main codebase.

* If your feature branch is not based off the latest master, you will be asked
  to rebase it before it is merged. This ensures that the commit history is
  linear, which makes the commit history easier to read.

* How do you rebase on to master, you ask? After `syncing your fork against
  the Orchestra master <https://help.github.com/articles/syncing-a-fork/>`_,
  run::

    git checkout master
    git pull
    git checkout your-branch
    git rebase master

* How do you squash changes, you ask? Easy::

    git log
    <find the commit hash that happened immediately before your first commit>
    git reset --soft $THAT_COMMIT_HASH$
    git commit -am "A commit message that summarizes all of your changes."
    git push -f origin your-branch

* Remember to reference any issues that your pull request fixes in the commit
  message, for example 'Fixes #12'. This will ensure that the issue is
  automatically closed when the PR is merged.

Quick Style Guide
#################

We generally stick to `PEP8 <http://legacy.python.org/dev/peps/pep-0008/>`_
for our coding style, use spaces for indenting, and make sure to wrap lines at
79 characters.

We have a linter built in to our test infrastructure, so ``make test``
won't succeed until the code is cleaned up. To run the linter standalone,
just run ``make lint``. Of course, sometimes you'll write code that will
never make the linter happy (for example, URL strings longer than 80
characters). In that case, just add a ``# noqa`` comment to the end of the line
to tell the linter to ignore it. But use this sparingly!
