class StaffingResponseException(Exception):
    pass


class SlackConnectionError(Exception):
    pass


class SlackCommandInvalidRequest(Exception):
    pass


class BaseBotError(Exception):
    pass
