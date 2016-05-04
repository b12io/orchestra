from orchestra.bots.staffbot import StaffBot


def staffbot_autoassign(task, **kwargs):
    bot = StaffBot()
    bot.staff(task.id)
