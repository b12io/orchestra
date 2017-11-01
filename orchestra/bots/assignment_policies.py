from orchestra.bots.staffbot import StaffBot
from orchestra.models import StaffBotRequest
from orchestra.utils.task_lifecycle import role_counter_required_for_new_task


def staffbot_autoassign(task, **kwargs):
    request_cause = StaffBotRequest.RequestCause.AUTOSTAFF.value
    bot = StaffBot()
    bot.staff(task.id, request_cause=request_cause)
    return task


def staffbot_request(task, **kwargs):
    required_role_counter = role_counter_required_for_new_task(task)
    StaffBotRequest.objects.create(
        task=task,
        required_role_counter=required_role_counter,
        request_cause=StaffBotRequest.RequestCause.USER.value
    )
    return task
