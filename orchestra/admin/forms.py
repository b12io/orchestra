from django import forms
from django.conf import settings

from orchestra.models import Project
from orchestra.models import Task
from orchestra.models import Worker
from orchestra.slack import SlackService
from orchestra.utils.settings import run_if
from orchestra.utils.task_lifecycle import assign_task
from orchestra.utils.task_properties import all_workers
from orchestra.utils.task_properties import current_assignment


class ProjectForm(forms.ModelForm):
    # TODO(jrbotros): display these only when slack API key present
    slack_name_to_add = forms.CharField(max_length=200, required=False)
    slack_name_to_remove = forms.CharField(max_length=200, required=False)

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)

    def clean(self):
        super(ProjectForm, self).clean()
        self._validate_slack_data()
        return self.cleaned_data

    def save(self, commit=True):
        self._save_slack_data()
        return super(ProjectForm, self).save(commit=commit)

    @run_if('SLACK_EXPERTS')
    def _validate_slack_data(self):
        slack_name_to_add = self.cleaned_data.get('slack_name_to_add',
                                                  None)
        slack_name_to_remove = self.cleaned_data.get('slack_name_to_remove',
                                                     None)

        slack = SlackService(settings.SLACK_EXPERTS_API_KEY)

        slack_id_to_add = slack.users.get_user_id(slack_name_to_add)
        slack_id_to_remove = slack.users.get_user_id(slack_name_to_remove)
        if ((slack_name_to_add and not slack_id_to_add) or
           (slack_name_to_remove and not slack_id_to_remove)):
            raise forms.ValidationError('Slack username does not exist.')

        self.cleaned_data['slack_id_to_add'] = slack_id_to_add
        self.cleaned_data['slack_id_to_remove'] = slack_id_to_remove

    @run_if('SLACK_EXPERTS')
    def _save_slack_data(self):
        slack = SlackService(settings.SLACK_EXPERTS_API_KEY)
        if self.cleaned_data['slack_id_to_add']:
            slack.groups.invite(self.instance.slack_group_id,
                                self.cleaned_data['slack_id_to_add'])
        if self.cleaned_data['slack_id_to_remove']:
            slack.groups.kick(self.instance.slack_group_id,
                              self.cleaned_data['slack_id_to_remove'])

    class Meta:
        model = Project
        fields = '__all__'


class TaskForm(forms.ModelForm):
    currently_assigned_to = forms.TypedChoiceField(required=False)

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        workers = Worker.objects.all()
        choices = [(None, None)] + [(w.id, w.user.username) for w in workers]
        self.fields['currently_assigned_to'].choices = choices

        if self._instance_created() and self.instance.assignments.exists():
            assignment = current_assignment(self.instance)
            if assignment.worker:
                # If human task, select human worker
                (self.fields['currently_assigned_to']
                     .initial) = assignment.worker.id

    def save(self, *args, **kwargs):
        # Create task before further modifications
        task = super(TaskForm, self).save(*args, **kwargs)

        new_worker_id = self.cleaned_data.get('currently_assigned_to', None)

        # TODO(jrbotros): write helper functions to move back and forth through
        # task statuses in the admin

        if (new_worker_id and
           new_worker_id not in [worker.id for worker in all_workers(task)]):
            # If no pre-existing worker is present or the selected worker
            # has not previously been involved with the task, (re)assign it.
            task = assign_task(new_worker_id, task.id)
        return task

    def _instance_created(self):
        return Task.objects.filter(id=self.instance.id).exists()

    class Meta:
        model = Task
        fields = '__all__'
