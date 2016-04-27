from django.db import models


class CommunicationPreferenceManager(models.Manager):

    def get_or_create_all_types(self, worker, methods=None):
        """
            Create CommunicationPreference objects with all of the given
            CommunicationTypes and the given methods flags.
        """

        methods = methods or self.model.get_default_methods()
        choices = self.model.CommunicationType.choices()
        comm_prefs = []
        for communication_type, _ in choices:
            comm_pref, _ = self.get_or_create(
                worker=worker,
                methods=methods,
                communication_type=communication_type
            )
            comm_prefs.append(comm_prefs)
        return comm_prefs
