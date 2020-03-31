from bitfield import BitField
from django.db import models

from orchestra.models.communication.managers import \
    CommunicationPreferenceManager
from orchestra.models.communication.mixins import CommunicationPreferenceMixin
from orchestra.models.communication.mixins import StaffBotRequestMixin
from orchestra.models.communication.mixins import StaffingRequestInquiryMixin
from orchestra.models.communication.mixins import StaffingResponseMixin
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
        NEW_TASK_AVAILABLE = 'new_task_available'

    COMMUNICATION_TYPE_DESCRIPTIONS = {
        CommunicationType.TASK_STATUS_CHANGE:
        {
            'short_description': 'Task Status Changes',
            'long_description':
            """
            When a task status changes (e.g., when it moves from in
            review to returned from reviewer), you will automatically
            receive a notification in the project Slack group. Select
            whether you would like to receive an email notification as
            well.
            """
        },
        CommunicationType.NEW_TASK_AVAILABLE:
        {
            'short_description': 'New Tasks',
            'long_description':
            """
            Select your preferred channel for being notified when a
            new task is available to work on.
            """
        }
    }

    worker = models.ForeignKey(Worker, on_delete=models.CASCADE)
    methods = BitField(flags=COMMUNICATION_METHODS,
                       blank=True, null=True, default=None)
    communication_type = models.IntegerField(
        choices=CommunicationType.choices())

    class Meta:
        app_label = 'orchestra'
        unique_together = (('worker', 'communication_type'),)


class StaffBotRequest(StaffBotRequestMixin, BaseModel):
    """
    A StaffBotRequest object defines a new task that needs
    a worker for a specific role.

    Attributes:
        task (orchestra.models.Task):
            The task that needs a worker assignment
        required_role_counter (int):
            Counter that tells which expert is a new worker
            going to be on a task
        request_cause (RequestCause):
            The cause for request
        project_description (str):
            Description of the project
        status (Status)
            Status of the request
        last_inquiry_sent (DateTimeField):
            The datetime the most recent inquiry was sent.
    """
    class RequestCause(ChoicesEnum):
        USER = 'user'
        AUTOSTAFF = 'autostaff'
        RESTAFF = 'restaff'

    class Status(ChoicesEnum):
        SENDING_INQUIRIES = 'sending inquiries'
        DONE_SENDING_INQUIRIES = 'done sending inquiries'
        CLOSED = 'closed'

    task = models.ForeignKey(
        Task, related_name='staffing_requests', on_delete=models.CASCADE)
    required_role_counter = models.IntegerField()
    request_cause = models.IntegerField(choices=RequestCause.choices())
    project_description = models.TextField(null=True, blank=True)
    status = models.IntegerField(
        default=Status.SENDING_INQUIRIES.value,
        choices=Status.choices())
    last_inquiry_sent = models.DateTimeField(null=True)


class StaffingRequestInquiry(StaffingRequestInquiryMixin, BaseModel):
    """
    A StaffingRequestInquiry object defines how a Worker was contacted to
    work on a StaffBotRequest

    Attributes:
        communication_preference (orchestra.models.CommunicationPreference):
            Django user that the request is sent to
        request (orchestra.models.StaffBotRequest):
            Request object associated with inquiry
        communication_method (CommunicationMethod):
            Method by which a worker is going to be contacted
    """

    class CommunicationMethod(ChoicesEnum):
        SLACK = 'slack'
        EMAIL = 'email'

    request = models.ForeignKey(StaffBotRequest,
                                on_delete=models.CASCADE,
                                null=True,
                                related_name='inquiries')
    communication_preference = models.ForeignKey(
        CommunicationPreference, on_delete=models.CASCADE)
    communication_method = models.IntegerField(
        choices=CommunicationMethod.choices())


class StaffingResponse(StaffingResponseMixin, BaseModel):
    """
    A StaffingResponse object stores a response from a worker and
    whether the worker got the task.

    Attributes:
        request_inquiry (orchestra.models.StaffingRequestInquiry):
            Request inquiry associated with a response
        response_text (str):
            Response text that a Worker provided
        is_available (bool):
            True if a Worker is ready to work on the Task
        is_winner (bool):
            True if a Worker was selected to work on the Task
    """
    request_inquiry = models.ForeignKey(StaffingRequestInquiry,
                                        on_delete=models.CASCADE,
                                        related_name='responses')
    response_text = models.TextField(blank=True, null=True)
    is_available = models.BooleanField()
    is_winner = models.NullBooleanField()
