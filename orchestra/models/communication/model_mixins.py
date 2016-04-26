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

    def __str__(self):
        return '{} - {} - {}'.format(
            self.worker,
            self.methods.items(),
            self.get_comunication_type_description()
        )
