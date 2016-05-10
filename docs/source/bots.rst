###############
Orchestra Bots
###############

Below, we'll walk through the various bots available in Orchestra.

*********
StaffBot
*********

``StaffBot`` provides a simple way to ask a group of Workers if they would like
to work on a particular ``Task``. The goal is reduce the human load when
finding a ``Worker`` for  a ``Task``. ``StaffBot`` allows a user to interact
with Orchestra via `Slack`_ or can be configured to automatically find workers for
a ``Task`` when it is available by setting up an `Assignment Policy`_.

``StaffBot`` works by reaching out to qualified workers and offering them the
``Task`` to work on. Workers can then accept or reject the task and starting
working on it.


Slack
=====

To interact with ``StaffBot`` via Slack, you first need to configure a `Slack
Slash Command <https://api.slack.com/slash-commands>`_. Below is a sample
configuration for the ``/staffbot`` command.


.. image:: ../static/img/bots/slash_command_config_token.png
.. image:: ../static/img/bots/slash_command_autocomplete.png

Once the command is created, copy the token for the command into your project
settings as follows: ``ORCHESTRA_SLACK_STAFFBOT_TOKEN = 'your-token-here'``.
The token is used to authenticated requests sent to the staffbot url. It is
important to keep this token secret since otherwise anyone may make a ``HTTP
POST`` and execute the staffing logic!

In addition to the ``ORCHESTRA_SLACK_STAFFBOT_TOKEN`` setting, you can further
restrict access to the endpoint by specifying the following setting::

 STAFFBOT_CONFIG = {
            'allowed_team_ids': ['allowed_team_ids'],
            'allowed_team_domains': ['allowed_domains'],
            'allowed_channel_ids': ['allowed_channel_ids'],
            'allowed_channel_names': ['allowed_channel_names'],
            'allowed_user_ids': ['allowed_user_ids'],
            'allowed_user_names': ['allowed_user_names'],
            'allowed_commands': ['allowed_commands'],
        }

``StaffBot`` will use the ``STAFFBOT_CONFIG`` to filter messages that do not
match items in the list. If a parameter is not specified, all values are
accepted by default.


Once this configuration is complete, you can test by typing ``/staffbot staff
<task-id>`` where ``<task-id>`` is an unassigned task.

Assignment Policy
================

``StaffBot`` can also work without user interaction by specifying an Assignment
Policy. Orchestra supports custom logic for assigning workers to tasks,
``StaffBot`` leverages this by asking qualified workers if they would like to
work on a ``Task`` as soon as the ``Task`` is available. To specify the
``StaffBot`` auto assignment policy, add the following to the ``Step``
configuration in your ``version.json`` file. Following the Journalism Workflow
Example we have::

  [...step definition...]
  "assignment_policy": {
      "policy_function": {
          "entry_level": {
              "path": "orchestra.bots.assignment_policies.staffbot_autoassign"
          }
      }
  },
  [...step definition...]

Now, for entry-level tasks within the defined step, ``StaffBot`` will
automatically try to staff this ``Task``. If the task requires review, manual
assignment is necessary unless we add a reviewer key to the policy function::

  [...step definition...]
  "assignment_policy": {
      "policy_function": {
          "entry_level": {
              "path": "orchestra.bots.assignment_policies.staffbot_autoassign"
          },
          "reviewer": {
              "path": "orchestra.bots.assignment_policies.staffbot_autoassign"
          }
      }
  },
  [...step definition...]

Detailed Description Function
=============================

The ``detailed_scription_function`` is used to dynamically describe a ``Task``
when ``StaffBot`` makes requests to workers offering them the opportunity to
work on the ``Task``. The function is given a ``task_details`` dictionary and
can be passed extra ``kwargs`` as shown below::

  [...step definition...]
  "detailed_description_function": {
       "path": "orchestra.tests.helpers.fixtures.get_detailed_description",
       "kwargs": {
           "text": "step 2 text"
       }
  }
  [...step definition...]
