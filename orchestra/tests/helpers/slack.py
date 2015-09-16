from unittest.mock import MagicMock

from django.conf import settings
import slacker


# Groups that are not dynamically created during testing
PREEXISTING_GROUPS = [settings.SLACK_INTERNAL_NOTIFICATION_CHANNEL]


class MockSlacker(MagicMock):
    def __init__(self, *args, **kwargs):
        super(MagicMock, self).__init__(*args, **kwargs)
        self.data = {
            'groups': {},
            'users': {},
            'invited': []
        }
        self.groups = Groups(self.data)
        self.chat = Chat(self.data)
        self.users = Users(self.data)
        self.populate_preexisting_groups()

    def populate_preexisting_groups(self):
        for group_name in PREEXISTING_GROUPS:
            self.groups.create(group_name)

    def get_messages(self, group_id):
        return self.data['groups'][group_id]['messages']

    def clear(self):
        self.data['groups'].clear()
        self.data['users'].clear()
        self.data['invited'][:] = []
        self.populate_preexisting_groups()


class BaseAPI(object):

    class Response(object):
        def __init__(self, body):
            self.body = body

    def __init__(self, data):
        self.data = data

    def _group_exists(self, group_id):
        return self.data['groups'].get(group_id, None) is not None

    def _user_exists(self, user_id):
        return self.data['users'].get(user_id, None) is not None

    def _validate_group(self, group_id):
        if not group_id or not self._group_exists(group_id):
            raise slacker.Error('Group not found.')

    def _validate_user(self, user_id):
        if not user_id or not self._user_exists(user_id):
            raise slacker.Error('User not found.')

    def post(self, command, data):
        if command == 'users.admin.invite':
            user_email = data.get('email', None)
            if user_email:
                if user_email not in self.data['invited']:
                    self.data['invited'].append(user_email)
            else:
                raise slacker.Error('User email was not provided')

    def accept_invite(self, email, username):
        """
        Imitate the user signing up for a slack account after invitation.
        """
        self.data['invited'].remove(email)
        # Mock user id is the same as username
        user_id = username
        self.data['users'][user_id] = {
            'email': email,
            'name': username
        }


class Groups(BaseAPI):
    def create(self, group_name):
        # Mock group id is the same as the group name
        group_id = str(group_name)
        self.data['groups'][group_id] = {
            'id': group_id,
            'users': [],
            'messages': [],
            'topic': None,
            'purpose': None
        }
        return self.Response({'group': self.data['groups'][group_id]})

    def invite(self, group_id, user_id):
        self._validate_group(group_id=group_id)
        self._validate_user(user_id=user_id)

        already_in_group = True
        if user_id not in self.data['groups'][group_id]['users']:
            # Slacker API does not raise an error if user already present
            self.data['groups'][group_id]['users'].append(user_id)
            already_in_group = False
        return self.Response({'already_in_group': already_in_group})

    def kick(self, group_id, user_id):
        self._validate_group(group_id=group_id)
        self._validate_user(user_id=user_id)

        if user_id not in self.data['groups'][group_id]['users']:
            raise slacker.Error('User does not belong to group.')

        # Slacker API does not raise an error if user already present
        self.data['groups'][group_id]['users'].remove(user_id)

    def set_topic(self, group_id, topic):
        self._validate_group(group_id=group_id)
        self.data['groups'][group_id]['topic'] = topic

    def set_purpose(self, group_id, purpose):
        if not self._group_exists(group_id):
            raise slacker.Error('Group not found.')

        self.data['groups'][group_id]['purpose'] = purpose


class Chat(BaseAPI):
    def post_message(self, group_id, text):
        self._validate_group(group_id=group_id)
        self.data['groups'][group_id]['messages'].append(text)


class Users(BaseAPI):
    def get_user_id(self, user_name):
        for uid, uname in self.data['users'].items():
            if uname == user_name:
                return uid
        return None
