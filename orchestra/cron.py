import kronos
from orchestra.communication.staffing import send_staffing_requests


@kronos.register('*/5 * * * *')
def send_staffing_requests_periodically():
    send_staffing_requests()
