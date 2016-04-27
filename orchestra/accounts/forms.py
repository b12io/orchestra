from django import forms
from django.contrib.auth import get_user_model

from orchestra.models import Worker

UserModel = get_user_model()


class UserForm(forms.ModelForm):
    first_name = forms.CharField()
    last_name = forms.CharField()

    class Meta:
        model = UserModel
        fields = ('first_name', 'last_name')
        # TODO(joshblum): support change email
        exclude = ('is_staff', 'is_active', 'date_joined', 'username', 'email')


class WorkerForm(forms.ModelForm):
    slack_username = forms.CharField()

    class Meta:
        model = Worker
        fields = ('slack_username',)
        exclude = ('user', 'start_datetime')
