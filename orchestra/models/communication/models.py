from bitfield import BitField
from django.db import models

from orchestra.models.communication.model_mixins import CommunicationPreferenceMixin  # noqa
from orchestra.models.communication.model_mixins import StaffingRequestMixin
from orchestra.models.communication.model_mixins import StaffingResponseMixin
from orchestra.models.communication.managers import CommunicationPreferenceManager  # noqa
from orchestra.models.core.models import Task
from orchestra.models.core.models import Worker
from orchestra.utils.models import BaseModel
from orchestra.utils.models import ChoicesEnum


class CommunicationPreference(CommunicationPreferenceMixin, BaseModel):
    """
        A CommunicationPreference object defines how a Worker would like to
        contacted for a given CommunicationType.

        Attributes:
            worker (orchestra.models.Worker):
                Django user that the preference represents.
            methods (BitField):
                The ways in which the user would like to be contacted.
            type (CommunicationType):
                The type of communication to which this preference applies.
    """
    objects = CommunicationPreferenceManager()

    class CommunicationMethods:
        SLACK = 'slack'
        EMAIL = 'email'

    COMMUNICATION_METHODS = (
        (CommunicationMethods.SLACK, 'Slack'),
        (CommunicationMethods.EMAIL, 'Email'),
    )

    class CommunicationType(ChoicesEnum):
        TASK_STATUS_CHANGE = 'task_status_change'

    COMMUNICATION_TYPE_DESCRIPTIONS = {
        CommunicationType.TASK_STATUS_CHANGE.description:
        {
            'short_description': 'Task Status Change',
            'long_description':
            """
            When a task status changes (e.g., moved from in review to returned
            from reviewer), you will automatically be alerted in a project
            slack group.  You can optionally receive email alerts.
            """
        }
    }

    worker = models.ForeignKey(Worker)
    methods = BitField(flags=COMMUNICATION_METHODS,
                       blank=True, null=True, default=None)
    communication_type = models.IntegerField(
        choices=CommunicationType.choices())

    class Meta:
        app_label = 'orchestra'
        unique_together = (('worker', 'communication_type'),)


class StaffingRequest(StaffingRequestMixin, BaseModel):
    """
    A StaffingRequest object defines how a Worker was contacted to
    work on a Task by staffbot.

    Attributes:
        worker (orchestra.models.Worker):
            Django user that the request is sent to
        task (orchestra.models.Task):
            The task that needs a worker assignment
        request_cause (RequestCause):
            The cause for request
        project_description (str):
            Description of the project
    """

    class RequestCause(ChoicesEnum):
        USER = 'user'
        AUTOSTAFF = 'autostaff'
        RESTAFF = 'restaff'

    class Status(ChoicesEnum):
        PENDING = 'pending'
        SENT = 'sent'

    class CommunicationMethod(ChoicesEnum):
        SLACK = 'slack'
        EMAIL = 'email'

    worker = models.ForeignKey(Worker)
    task = models.ForeignKey(Task)
    request_cause = models.IntegerField(choices=RequestCause.choices())
    project_description = models.TextField(null=True, blank=True)
    status = models.IntegerField(
        default=Status.PENDING.value,
        choices=Status.choices())
    communication_method = models.IntegerField(
        choices=CommunicationMethod.choices())


class StaffingResponse(StaffingResponseMixin, BaseModel):
    """
    A StaffingResponse object stores a response from a worker and
    whether the worker got the task.

    Attributes:
        request (orchestra.models.StaffingRequest):
            Request object associated with a response
        response_text (str):
            Response text that a Worker provided
        is_available (bool):
            True if a Worker is ready to work on the Task
        is_winner (bool):
            True if a Worker was selected to work on the Task
    """

    request = models.ForeignKey(StaffingRequest, related_name='responses')
    response_text = models.TextField(blank=True, null=True)
    is_available = models.BooleanField()
    is_winner = models.NullBooleanField()
