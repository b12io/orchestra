class MockMail:
    def __init__(self):
        self.inbox = []

    def send_mail(self, recipient_list, **kwargs):
        for recipient in recipient_list:
            self.inbox.append({
                'recipient': recipient,
                'subject': kwargs['subject'],
                'message': kwargs['message']
            })

    def clear(self):
        self.inbox[:] = []
