from unittest.mock import MagicMock

import slacker
from django.conf import settings

# Groups that are not dynamically created during testing
PREEXISTING_GROUPS = [settings.SLACK_INTERNAL_NOTIFICATION_CHANNEL]


MOCK_SLACK_API_DATA = {
    'channels': {},
    'users': {},
    'invited': [],
}


class MockSlacker(MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.data = MOCK_SLACK_API_DATA
        self.conversations = Conversations()
        self.chat = Chat()
        self.users = Users()
        self.populate_preexisting_groups()

    def populate_preexisting_groups(self):
        for group_name in PREEXISTING_GROUPS:
            self.conversations.create(group_name, is_private=True)

    def get_messages(self, group_id):
        return MOCK_SLACK_API_DATA['channels'][group_id]['messages']

    def clear(self):
        MOCK_SLACK_API_DATA['channels'].clear()
        MOCK_SLACK_API_DATA['users'].clear()
        MOCK_SLACK_API_DATA['invited'][:] = []
        self.populate_preexisting_groups()


class BaseAPI(object):

    class Response(object):
        def __init__(self, body):
            self.body = body

    def _group_exists(self, group_id):
        return MOCK_SLACK_API_DATA['channels'].get(group_id, None) is not None

    def _user_exists(self, user_id):
        return MOCK_SLACK_API_DATA['users'].get(user_id, None) is not None

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
                if user_email not in MOCK_SLACK_API_DATA['invited']:
                    MOCK_SLACK_API_DATA['invited'].append(user_email)
            else:
                raise slacker.Error('User email was not provided')

    def accept_invite(self, email, username):
        """
        Imitate the user signing up for a slack account after invitation.
        """
        MOCK_SLACK_API_DATA['invited'].remove(email)
        # Mock user id is the same as username
        user_id = username
        MOCK_SLACK_API_DATA['users'][user_id] = {
            'email': email,
            'name': username
        }


class Conversations(BaseAPI):
    def create(self, group_name, is_private=False):
        group_id = str(len(MOCK_SLACK_API_DATA['channels']))
        MOCK_SLACK_API_DATA['channels'][group_id] = {
            'id': group_id,
            'users': [],
            'messages': [],
            'topic': None,
            'purpose': None,
            'name': group_name.strip('#'),
        }
        return self.Response({
            'channel': MOCK_SLACK_API_DATA['channels'][group_id]
        })

    def invite(self, group_id, user_id):
        self._validate_group(group_id=group_id)
        self._validate_user(user_id=user_id)
        if user_id not in MOCK_SLACK_API_DATA['channels'][group_id]['users']:
            # Slacker API does not raise an error if user already present
            MOCK_SLACK_API_DATA['channels'][group_id]['users'].append(user_id)
        return self.Response({})

    def info(self, group_id):
        self._validate_group(group_id=group_id)
        return self.Response({
            'ok': True,
            'channel': {
                'id': group_id,
                'is_archived': True
            }
        })

    def kick(self, group_id, user_id):
        self._validate_group(group_id=group_id)
        self._validate_user(user_id=user_id)

        if user_id not in MOCK_SLACK_API_DATA['channels'][group_id]['users']:
            raise slacker.Error('User does not belong to group.')

        # Slacker API does not raise an error if user already present
        MOCK_SLACK_API_DATA['channels'][group_id]['users'].remove(user_id)

    def set_topic(self, group_id, topic):
        self._validate_group(group_id=group_id)
        MOCK_SLACK_API_DATA['channels'][group_id]['topic'] = topic

    def set_purpose(self, group_id, purpose):
        if not self._group_exists(group_id):
            raise slacker.Error('Group not found.')

        MOCK_SLACK_API_DATA['channels'][group_id]['purpose'] = purpose

    def list(self):
        return self.Response({
            'ok': True,
            'channels': list(MOCK_SLACK_API_DATA['channels'].values())
        })

    def archive(self, group_id):
        self._validate_group(group_id=group_id)
        return self.Response({
            'ok': True
        })

    def unarchive(self, group_id):
        self._validate_group(group_id=group_id)
        return self.Response({
            'ok': True
        })


class Chat(BaseAPI):
    def post_message(self, group_identifier, text, parse='none'):
        if group_identifier.startswith('#'):
            groups = [
                group for group in MOCK_SLACK_API_DATA['channels'].values()
                if group['name'] == group_identifier.strip('#')]
            group_identifier = groups[0]['id']
        self._validate_group(group_id=group_identifier)
        MOCK_SLACK_API_DATA[
            'channels'][group_identifier]['messages'].append(text)


class Users(BaseAPI):
    def get_user_id(self, user_name):
        for uid, uname in MOCK_SLACK_API_DATA['users'].items():
            if uname == user_name:
                return uid
        return None
