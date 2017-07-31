####################################################
#     ____  ___ _____   _________    _   __
#    / __ )/   /__  /  / ____/   |  / | / /
#   / __  / /| | / /  / __/ / /| | /  |/ /
#  / /_/ / ___ |/ /__/ /___/ ___ |/ /|  /
# /_____/_/  |_/____/_____/_/  |_/_/ |_/
#
# COPYRIGHT 2017 | BAZEAN CORP | All Rights Reserved
# Author: Nikola Nik
#
####################################################

# PagerDuty module
# Sends alerts

import requests
import json

class PagerDuty(object):
    def __init__(self, api_key='-Ks2iJy2CUhK7p1dR7B-', service_integration_key='bc3c3cf6bd3b4fe19fc376806f4654af', service_key='PYE1CJA'):
        self.api_key = api_key
        self.service_int egration_key = service_integration_key
        self.service_key = service_key

    def send_alert(self, description, client):
        url = 'https://events.pagerduty.com/generic/2010-04-15/create_event.json'
        data = {    
            'service_key': self.service_integration_key,
            'event_type': 'trigger',
            'description': description,
            'client': client,
        }
        try:
            response = requests.post(url, data=json.dumps(data))
        except:
            return False

        if response.status_code == 200:
            return json.loads(response.text)
        else:
            return False
