from orchestra.bots.staffbot import StaffBot
from orchestra.models import StaffingRequestInquiry


def staffbot_autoassign(task, **kwargs):
    request_cause = StaffingRequestInquiry.RequestCause.AUTOSTAFF.value
    bot = StaffBot()
    bot.staff(task.id, request_cause=request_cause)
