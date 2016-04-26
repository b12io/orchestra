from bitfield import BitField
from django.db import models

from orchestra.models.communication.model_mixins import CommunicationPreferenceMixin  # noqa
from orchestra.models.core.models import Worker
from orchestra.utils.models import ChoicesEnum


class CommunicationPreference(CommunicationPreferenceMixin, models.Model):
    """
    A CommunicationPreference object defines how a User would like to contacted
    for a given CommunicationType.

    Attributes:
        worker (orchestra.models.Worker):
            Django user that the preference represents.
        methods (BitField):
            The ways in which the user would like to be contacted.
        type (CommunicationType):
            The type of communication to which this preference applies.
    """

    class CommunicationMethods:
        SLACK = 'slack'
        EMAIL = 'email'

    COMMUNICATION_METHODS = (
        (CommunicationMethods.SLACK, 'Slack'),
        (CommunicationMethods.EMAIL, 'Email'),
    )

    class CommunicationType(ChoicesEnum):
        TASK_STATUS_CHANGE = 'task_status_change'

    worker = models.ForeignKey(Worker)
    methods = BitField(flags=COMMUNICATION_METHODS,
                       blank=True, null=True, default=None)

    communication_type = models.IntegerField(
        choices=CommunicationType.choices())

    class Meta:
        app_label = 'orchestra'
        unique_together = (('worker', 'communication_type'),)
