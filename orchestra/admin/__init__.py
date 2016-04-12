from django.contrib import admin

from orchestra.models import Certification
from orchestra.models import PayRate
from orchestra.models import Project
from orchestra.models import Step
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TimeEntry
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.models import Workflow
from orchestra.models import WorkflowVersion

admin.site.register(Certification)
admin.site.register(Project)
admin.site.register(PayRate)
admin.site.register(Step)
admin.site.register(Task)
admin.site.register(TaskAssignment)
admin.site.register(Worker)
admin.site.register(WorkerCertification)
admin.site.register(Workflow)
admin.site.register(WorkflowVersion)


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'worker', 'time_worked', 'assignment')
    search_fields = ('id', 'worker')


admin.site.site_header = 'Orchestra'
admin.site.site_title = 'Orchestra'
admin.site.index_title = 'Orchestra'
