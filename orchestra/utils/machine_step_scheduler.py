from beanstalk_dispatch.client import schedule_function
from django.conf import settings

from orchestra.machine_tasks import execute


class MachineStepScheduler(object):
    def schedule(self, project_id, step_slug):
        raise NotImplementedError()


class SynchronousMachineStepScheduler(MachineStepScheduler):
    def schedule(self, project_id, step_slug):
        execute(project_id, step_slug)


class AsynchronousMachineStepScheduler(MachineStepScheduler):
    def schedule(self, project_id, step_slug):
        if not settings.PRODUCTION and not settings.STAGING:
            scheduler = SynchronousMachineStepScheduler()
            scheduler.schedule(project_id, step_slug)
        else:
            schedule_function(settings.WORK_QUEUE, 'machine_task_executor',
                              project_id, step_slug)
