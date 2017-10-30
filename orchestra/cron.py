import kronos
from orchestra.communication.staffing import send_staffing_requests


@kronos.register('* * * * *')  # run every minute
def send_staffing_requests_periodically():
    print('yolo')
    send_staffing_requests()
