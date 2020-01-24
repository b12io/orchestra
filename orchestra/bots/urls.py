from django.conf.urls import url

from orchestra.bots.views import StaffBotView

app_name = 'bots'

urlpatterns = [
    url(r'^staffbot/$',
        StaffBotView.as_view(), name='staffbot'),
]
