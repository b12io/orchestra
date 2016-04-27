from django.db import models


class CommunicationPreferenceManager(models.Manager):

    def create_all_types(self, worker, methods=None):
        """
            Create CommunicationPreference objects with all of the given
            CommunicationTypes and the given methods flags.
        """

        methods = methods or self.model.get_default_methods()
        choices = self.model.CommunicationType.choices()
        for communication_type, _ in choices:
            self.create(
                worker=worker,
                methods=methods,
                communication_type=communication_type
            )
