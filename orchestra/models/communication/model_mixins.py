class CommunicationPreferenceMixin(object):

    @classmethod
    def get_default_methods(cls):
        """
            We want to set every value in the bitfield to 1.
        """
        return 2 ** len(cls.COMMUNICATION_METHODS) - 1

    def __str__(self):
        description = self.CommunicationType.get_description(
            self.communication_type)
        return '{} - {} - {}'.format(
            self.worker, self.methods.items(), description
        )
