from django.conf.urls import url
from beanstalk_dispatch.views import dispatcher

urlpatterns = [
    url(r'^', dispatcher, name='beanstalk_dispatcher')
]
