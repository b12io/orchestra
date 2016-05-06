class StaffingResponseException(Exception):
    pass


class SlackConnectionError(Exception):
    pass


class SlackUserUnauthorized(Exception):
    pass


class SlackCommandInvalidRequest(Exception):
    pass
