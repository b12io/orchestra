from django.db import models


class CommunicationPreferenceManager(models.Manager):

    def get_or_create_all_types(self, worker, methods=None):
        """
            Create CommunicationPreference objects with all of the given
            CommunicationTypes and the given methods flags.
        """

        methods = methods or self.model.get_default_methods()
        choices = self.model.CommunicationType.choices()
        for communication_type, _ in choices:
            self.get_or_create(
                worker=worker,
                methods=methods,
                communication_type=communication_type
            )
