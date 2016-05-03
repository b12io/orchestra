

def get_mock_slack_data(
        token='test-token',
        team_id='test-team-id',
        team_domain='test-team-domain',
        channel_id='test-channel-id',
        channel_name='test-channel-name',
        user_id='test-user-id',
        user_name='test-user-name',
        command='/test',
        text='test-text'):
    return {
        'token': token,
        'team_id': team_id,
        'team_domain': team_domain,
        'channel_id': channel_id,
        'channel_name': channel_name,
        'user_id': user_id,
        'user_name': user_name,
        'command': command,
        'text': text,
    }
