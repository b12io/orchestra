class CommunicationPreferenceMixin(object):

    @classmethod
    def get_default_methods(cls):
        """
            We want to set every value in the bitfield to 1.
        """
        return 2 ** len(cls.COMMUNICATION_METHODS) - 1

    def get_comunication_type_description(self):
        return self.CommunicationType(
            self.communication_type).description

    def _can_send_communication(self, communication_method):
        """
            Determine if the user allows a given CommunicationMethod
        """
        return getattr(self.methods, communication_method).is_set

    def can_slack(self):
        """
            Boolean of whether or not the Worker wants slack messages
            for the CommunicationType.
        """
        return self._can_send_communication(self.CommunicationMethods.SLACK)

    def can_email(self):
        """
            Boolean of whether or not the Worker wants email messages
            for the CommunicationType.
        """
        return self._can_send_communication(self.CommunicationMethods.EMAIL)

    def __str__(self):
        return '{} - {} - {}'.format(
            self.worker,
            self.methods.items(),
            self.get_comunication_type_description()
        )


class StaffingRequestMixin(object):

    def get_request_cause_description(self):
        return self.RequestCause(self.request_cause).description

    def __str__(self):
        return '{} - {} - {}'.format(
            self.worker,
            self.task.id,
            self.get_request_cause_description()
        )


class StaffingResponseMixin(object):

    def __str__(self):
        return '{} - {}'.format(
            self.request,
            self.response_flags.items()
        )
