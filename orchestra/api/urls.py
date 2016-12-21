from rest_framework import routers

from orchestra.api.views import WorkerViewSet
from orchestra.api.views import WorkerCertificationViewSet
from orchestra.api.views import ProjectViewSet
from orchestra.api.views import TaskViewSet
from orchestra.api.views import TaskAssignmentViewSet
from orchestra.api.views import TimeEntryViewSet
from orchestra.api.views import IterationViewSet

api_router = routers.SimpleRouter()

api_router.register(
    r'iteration', IterationViewSet,
    base_name='iteration')

api_router.register(
    r'project', ProjectViewSet,
    base_name='project')

api_router.register(
    r'task', TaskViewSet,
    base_name='task')

api_router.register(
    r'taskassignment', TaskAssignmentViewSet,
    base_name='taskassignment')

api_router.register(
    r'timeentry', TimeEntryViewSet,
    base_name='timeentry')

api_router.register(
    r'worker', WorkerViewSet,
    base_name='worker')

api_router.register(
    r'workercertification', WorkerCertificationViewSet,
    base_name='workercertification')

urlpatterns = api_router.urls
