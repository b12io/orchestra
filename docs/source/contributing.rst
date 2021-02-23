How to contribute to Orchestra
==============================

So you want to get involved in developing Orchestra. Great! We're excited to
have your support. This document lays down a few guidelines to help the whole
process run smoothly.

Getting involved
################

First, if you find a bug in the code or documentation, check out
our `open issues <https://github.com/b12io/orchestra/issues>`_ and
`pull requests <https://github.com/b12io/orchestra/pulls>`_ to see if
we're already aware of the problem. Also feel free to reach out to us on
the `discussion forum <https://github.com/b12io/orchestra/discussions>`_
to ask questions or make suggestions.

If you've uncovered something new, please `create an issue
<https://github.com/b12io/orchestra/issues>`_ describing the problem.
If you've written code that fixes an issue, `create a pull request
<https://help.github.com/articles/creating-a-pull-request/>`_ (PR) so it's easy
for us to incorporate your changes.

Setting up for Development
##########################

We have a `.editorconfig` specified in the top level providing editor defaults
for our code style. We recommend to install an `EditorConfig
plugin <http://editorconfig.org/#download>`_ so your editor automatically adheres to our
style :).

We recommend using a `virtualenv <https://virtualenv.pypa.io/en/latest/>`_ to
install the required packages in ``requirements.txt``. In addition, we use
`Gulp <http://gulpjs.com/>`_ as a frontend build system.  To build the frontend
resources you can run ``make gulp_build`` once `npm <https://www.npmjs.com/>`_
is installed.

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
  <https://en.wikipedia.org/wiki/Code_coverage>`_. Aim for 100% for every new
  file you create!

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

When working on frontend resources, we use `Gulp <http://gulpjs.com/>`_ as a
frontend build system. This means that after making any changes to frontend
resources, you must run ``make gulp_build`` to include the modified resources.  This
moves resources to the ``build`` folder, compiling scss and linting your
javascript.

For stylesheets we only compile scss files so if your file is at
``orchestra/common/static/common/scss/example.scss``, to include it in an HTML
file you should write ``{% static 'common/css/example.css' %}">`` as the static
file path.

When including angular templates, we wrap references to static files with the
function ``$static(static_url_path)``. The ``$static`` function is defined in
the base template, and for development simply returns the url it is given. The
purpose is to decouple static file storage from the Django path, so if you host
your static files on a CDN, you can simply override this function and put the
appropriate urls.
