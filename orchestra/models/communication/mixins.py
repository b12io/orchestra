class CommunicationPreferenceMixin(object):

    @classmethod
    def get_default_methods(cls):
        """
            We want to set every value in the bitfield to 1.
        """
        return 2 ** len(cls.COMMUNICATION_METHODS) - 1

    def get_descriptions(self):
        key = self.CommunicationType(self.communication_type)
        return self.COMMUNICATION_TYPE_DESCRIPTIONS[key]

    def can_slack(self):
        """
            Boolean of whether or not the Worker wants slack messages
            for the CommunicationType.
        """
        return self.methods.slack

    def can_email(self):
        """
            Boolean of whether or not the Worker wants email messages
            for the CommunicationType.
        """
        return self.methods.email

    def __str__(self):
        return '{} - {} - {}'.format(
            self.worker,
            self.methods,
            self.get_descriptions().get('short_description')
        )


class StaffBotRequestMixin(object):

    def get_request_cause_description(self):
        return self.RequestCause(self.request_cause).description

    def __str__(self):
        return '{} - {} - {}'.format(
            self.task.id,
            self.get_request_cause_description(),
            self.required_role_counter
        )


class StaffingRequestInquiryMixin(object):

    def __str__(self):
        return '{} - {}'.format(
            self.communication_preference.worker,
            self.request.task.id
        )


class StaffingResponseMixin(object):

    def __str__(self):
        return '{} - {} - {}'.format(
            self.request_inquiry,
            self.is_available,
            self.is_winner
        )
