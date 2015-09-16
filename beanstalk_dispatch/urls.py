from django.conf.urls import patterns
from django.conf.urls import url
from beanstalk_dispatch.views import dispatcher

urlpatterns = patterns(
    '',
    url(r'^', dispatcher, name='beanstalk_dispatcher'))
