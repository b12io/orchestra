from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.generic import View

from orchestra.bots.errors import SlackCommandInvalidRequest
from orchestra.bots.staffbot import Bot
from orchestra.bots.staffbot import StaffBot


@method_decorator(login_required, name='dispatch')
class BotMixin(View):
    """
        Generic mixin to handle messages to bots, should be used by specifying
        a `BotClass` to instantiate with the request data.
    """
    BotClass = Bot
    bot_config = {}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = self.BotClass(**self.bot_config)

    def post(self, request, *args, **kwargs):
        data = request.POST
        try:
            response_data = self.bot.dispatch(data)
        except SlackCommandInvalidRequest as e:
            response_data = {'error': str(e)}
        return JsonResponse(response_data)


class StaffBotView(BotMixin):
    BotClass = StaffBot
