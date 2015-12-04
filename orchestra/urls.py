from django.conf.urls import include
from django.conf.urls import patterns
from django.conf.urls import url
from orchestra.views import index
from orchestra.views import status


urlpatterns = patterns(
    '',
    url(r'^api/',
        include('orchestra.api_urls', namespace='orchestra')),
    url(r'^app/?', index, name='index'),
    url(r'^status/', status, name='status')
)
