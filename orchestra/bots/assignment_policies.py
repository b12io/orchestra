from orchestra.bots.staffbot import StaffBot
from orchestra.models import StaffBotRequest


def staffbot_autoassign(task, **kwargs):
    request_cause = StaffBotRequest.RequestCause.TASK_POLICY.value
    bot = StaffBot()
    bot.staff(task.id, request_cause=request_cause)
    return task
