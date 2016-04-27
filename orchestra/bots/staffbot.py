class StaffBot(object):

    def __init__(self, slack_client):
        self.slack_client = slack_client

    def process_new_messages(self):
        new_messages = self.slack_client.rtm_read()
        print(new_messages)
