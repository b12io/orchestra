from ajax_select import LookupChannel
from ajax_select import register
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.utils.html import escape

from orchestra.models import CommunicationPreference
from orchestra.models import Project
from orchestra.models import StaffingRequestInquiry
from orchestra.models import Task
from orchestra.models import Worker

UserModel = get_user_model()


class FormatedItemMixin(object):
    url_reverse = ''

    def get_object_id(self, obj):
        return obj.id

    def format_item_display(self, obj):
        """ (HTML) formatted item for display in the dropdown """
        return '<div><a href="{}">{}</a></div>'.format(
            reverse(self.url_reverse, args=[self.get_object_id(obj)]),
            escape(obj)
        )


@register('users')
class UsersLookup(FormatedItemMixin, LookupChannel):

    model = UserModel
    url_reverse = 'admin:auth_user_change'

    def get_query(self, q, request):
        return self.model.objects.filter(
            Q(username__icontains=q) |
            Q(first_name__icontains=q) |
            Q(last_name__icontains=q) |
            Q(email__icontains=q))


@register('workers')
class WorkerLookup(FormatedItemMixin, LookupChannel):

    model = Worker
    url_reverse = 'admin:orchestra_worker_change'

    def get_query(self, q, request):
        return self.model.objects.filter(
            Q(user__first_name__icontains=q) |
            Q(user__last_name__icontains=q) |
            Q(user__email__icontains=q) |
            Q(user__username__icontains=q) |
            Q(slack_username__icontains=q))


@register('communication_preferences')
class CommunicationPreferenceLookup(FormatedItemMixin, LookupChannel):

    model = CommunicationPreference
    url_reverse = 'admin:orchestra_communicationpreference_change'

    def get_query(self, q, request):
        return self.model.objects.filter(
            Q(worker__user__first_name__icontains=q) |
            Q(worker__user__last_name__icontains=q) |
            Q(worker__user__email__icontains=q) |
            Q(worker__user__username__icontains=q) |
            Q(worker__slack_username__icontains=q))


@register('task_assignments')
class TaskAssignmentLookup(FormatedItemMixin, LookupChannel):

    model = Task
    url_reverse = 'admin:orchestra_taskassignment_change'

    def get_query(self, q, request):
        return self.model.objects.filter(
            Q(step__slug__icontains=q) |
            Q(project__short_description__icontains=q))


@register('tasks')
class TaskLookup(FormatedItemMixin, LookupChannel):

    model = Task
    url_reverse = 'admin:orchestra_task_change'

    def get_query(self, q, request):
        return self.model.objects.filter(
            Q(step__slug__icontains=q) |
            Q(project__short_description__icontains=q))


@register('staffing_request_inquiries')
class StaffingRequestInquiryLookup(FormatedItemMixin, LookupChannel):

    model = StaffingRequestInquiry
    url_reverse = 'admin:orchestra_staffingrequestinquiry_change'

    def get_query(self, q, request):
        return self.model.objects.filter(
            Q(
                communication_preference__worker__user__first_name__icontains=q
            ) |
            Q(communication_preference__worker__user__last_name__icontains=q) |
            Q(communication_preference__worker__user__email__icontains=q) |
            Q(communication_preference__worker__user__username__icontains=q) |
            Q(communication_preference__worker__slack_username__icontains=q) |
            Q(task__step__slug__icontains=q) |
            Q(task__project__short_description__icontains=q))


@register('projects')
class ProjectLookup(FormatedItemMixin, LookupChannel):

    model = Project
    url_reverse = 'admin:orchestra_project_change'

    def get_query(self, q, request):
        return self.model.objects.filter(
            Q(short_description__icontains=q) |
            Q(workflow_version__slug__icontains=q))
