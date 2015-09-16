from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import redirect
from django_object_actions import DjangoObjectActions

from orchestra.models import Certification
from orchestra.models import Worker
from orchestra.models import WorkerCertification
from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.admin.forms import ProjectForm
from orchestra.admin.forms import TaskForm
from orchestra.utils.task_lifecycle import end_project
from orchestra.utils.task_lifecycle import task_history_details


class ProjectAdmin(DjangoObjectActions, admin.ModelAdmin):
    form = ProjectForm

    objectactions = ('project_details', 'end_project_admin',)

    def project_details(self, request, project):
        return redirect('orchestra:project_details', project_id=project.id)
    project_details.label = 'Project Details'

    def end_project_admin(self, request, project):
        end_project(project.id)
        self.message_user(request, 'Project successfully ended.')

    end_project_admin.short_description = (
        'End project and mark all tasks as complete.')
    end_project_admin.label = 'End project'
    end_project_admin.attrs = {
        'onclick': ('return confirm("Are you sure you wish to end the '
                    'project?");')
    }


class TaskAdmin(admin.ModelAdmin):
    form = TaskForm

    def change_view(self, request, task_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['current_assignment'] = None
        extra_context['assignment_history'] = None
        try:
            extra_context.update(task_history_details(task_id))
        except ObjectDoesNotExist:
            # Task has not yet been created
            pass
        return super(TaskAdmin, self).change_view(request,
                                                  task_id,
                                                  form_url,
                                                  extra_context=extra_context)


admin.site.register(Certification)
admin.site.register(Worker)
admin.site.register(WorkerCertification)
admin.site.register(Project, ProjectAdmin)
admin.site.register(Task, TaskAdmin)
admin.site.register(TaskAssignment)

admin.site.site_header = 'Orchestra'
admin.site.site_title = 'Orchestra'
admin.site.index_title = 'Orchestra'
