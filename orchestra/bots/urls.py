from django.urls import re_path

from orchestra.bots.views import StaffBotView

app_name = 'bots'

urlpatterns = [
    re_path(r'^staffbot/$',
            StaffBotView.as_view(), name='staffbot'),
]
