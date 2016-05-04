from orchestra.bots.staffbot import StaffBot
from orchestra.models import StaffingRequest


def staffbot_autoassign(task, **kwargs):
    request_cause = StaffingRequest.RequestCause.AUTOSTAFF.value
    bot = StaffBot()
    bot.staff(task.id, request_cause=request_cause)
