from bitfield import BitField
from bitfield.admin import BitFieldListFilter
from bitfield.forms import BitFieldCheckboxSelectMultiple
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils.html import format_html
from phonenumber_field.modelfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget

from orchestra.models import Certification
from orchestra.models import Iteration
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
from orchestra.models import CommunicationPreference
from orchestra.models import StaffingRequestInquiry
from orchestra.models import StaffingResponse
from orchestra.communication.slack import get_slack_user_id

admin.site.site_header = 'Orchestra'
admin.site.site_title = 'Orchestra'
admin.site.index_title = 'Orchestra'


@admin.register(Certification)
class CertificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'slug', 'workflow', 'name')
    ordering = ('slug',)
    search_fields = ('slug', 'description', 'name')
    list_filter = ('workflow',)


@admin.register(Iteration)
class IterationAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'edit_assignment', 'start_datetime', 'end_datetime',
        'status')
    search_fields = (
        'assignment__task__step__name',
        'assignment__task__project__short_description'
        'assignment__worker__user__username')
    ordering = ('assignment__worker__user__username',)
    list_filter = ('status', 'assignment__worker__user__username')

    def edit_assignment(self, obj):
        return edit_link(obj.assignment)


@admin.register(PayRate)
class PayRateAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'edit_worker', 'hourly_rate', 'hourly_multiplier', 'start_date',
        'end_date')
    search_fields = ('worker__user__username',)
    ordering = ('worker__user__username',)
    list_filter = ('worker',)

    def edit_worker(self, obj):
        return edit_link(obj.worker)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'short_description', 'workflow_version', 'start_datetime')
    ordering = ('start_datetime',)
    search_fields = ('short_description',
                     'workflow_version__slug',
                     'workflow_version__workflow__slug',)
    list_filter = ('workflow_version',)


@admin.register(Step)
class StepAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'slug', 'workflow_version', 'name', 'description', 'is_human')
    ordering = ('slug',)
    search_fields = ('slug', 'name', 'description',)
    list_filter = ('workflow_version', 'is_human')


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'edit_project', 'step_name', 'workflow_version',
        'start_datetime')
    ordering = ('-project', 'start_datetime',)
    search_fields = ('project__short_description', 'step__name',)
    list_filter = ('step__is_human', 'project__workflow_version')

    def step_name(self, obj):
        return obj.step.name

    def workflow_version(self, obj):
        return obj.project.workflow_version

    def edit_project(self, obj):
        return edit_link(obj.project, obj.project.short_description)


@admin.register(TaskAssignment)
class TaskAssignmentAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'edit_project', 'edit_task', 'assignment_counter', 'edit_worker',
        'workflow_version', 'start_datetime')
    ordering = ('-task__project', 'task__start_datetime', 'assignment_counter')
    search_fields = (
        'task__project__short_description', 'task__step__name',
        'worker__user__username')
    list_filter = ('task__step__is_human', 'task__project__workflow_version')

    def workflow_version(self, obj):
        return obj.task.project.workflow_version

    def edit_task(self, obj):
        return edit_link(obj.task, obj.task.step.name)

    def edit_project(self, obj):
        return edit_link(obj.task.project, obj.task.project.short_description)

    def edit_worker(self, obj):
        return edit_link(obj.worker)


@admin.register(TimeEntry)
class TimeEntryAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'worker', 'time_worked', 'assignment')
    search_fields = (
        'id', 'worker__user__username', 'assignment__task__step__name',
        'assignment__task__project__short_description')
    list_filter = ('worker',)


@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('id', 'edit_user', 'email', 'slack_username', 'phone')
    ordering = ('user__username',)
    readonly_fields = ('slack_user_id',)
    search_fields = ('user__username', 'user__email', 'slack_username')

    formfield_overrides = {
        PhoneNumberField: {'widget': PhoneNumberPrefixWidget(initial='US')},
    }

    def save_model(self, request, obj, form, change):
        instance = form.save(commit=False)
        instance.slack_user_id = get_slack_user_id(
            form.data.get('slack_username'))
        instance.save()

    def edit_user(self, obj):
        return edit_link(obj.user, obj.user.username)

    def email(self, obj):
        return obj.user.email


@admin.register(WorkerCertification)
class WorkerCertificationAdmin(admin.ModelAdmin):
    list_display = ('id', 'worker', 'certification', 'role', 'task_class')
    search_fields = (
        'worker__user__username', 'certification__slug', 'certification__name',
        'certification__workflow__slug', 'certification__workflow__name',
        'certification__workflow__description')
    ordering = ('-created_at',)
    list_filter = ('task_class', 'role')


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'slug', 'name', 'description')
    ordering = ('slug',)
    search_fields = ('slug', 'name', 'description',)


@admin.register(WorkflowVersion)
class WorkflowVersionAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'slug', 'workflow', 'name', 'description')
    ordering = ('workflow__slug',)
    search_fields = ('workflow__slug', 'slug', 'name', 'description')
    list_filter = ('workflow',)


@admin.register(CommunicationPreference)
class CommunicationPreferenceAdmin(admin.ModelAdmin):
    formfield_overrides = {
        BitField: {'widget': BitFieldCheckboxSelectMultiple},
    }
    list_display = (
        'id', 'worker', 'methods', 'communication_type'
    )
    search_fields = ('worker__user__username', 'methods', 'communication_type')
    list_filter = ('worker__user__username', ('methods', BitFieldListFilter))


@admin.register(StaffingRequestInquiry)
class StaffingRequestInquiryAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'project_description',
    )
    search_fields = (
        'communication_preference__worker__user__username',
        'communication_type', 'project_description'
    )


@admin.register(StaffingResponse)
class StaffingResponseAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'request'
    )
    search_fields = (
        'request__communication_preference__worker__user__username',
        'request__communication_type', 'request__project_description'
    )


def edit_link(instance, text=None):
    if not instance:
        return None
    if text is None:
        text = str(instance)
    change_url_name = 'admin:{}_{}_change'.format(
        instance._meta.app_label, instance._meta.model_name)
    change_url = reverse(change_url_name, args=(instance.id,))
    return linkify(change_url, text=text)


def linkify(url, text=None, new_window=False):
    if text is None:
        text = url
    target_string = ''
    if new_window:
        target_string = '_blank'
    return format_html(
        '<a href="{}" target="{}">{}</a>', url, target_string, text)
