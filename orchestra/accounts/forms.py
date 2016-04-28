from django import forms
from django.contrib.auth import get_user_model
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget

from orchestra.accounts.bitformfield import BitFormField
from orchestra.models import CommunicationPreference
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
    phone = PhoneNumberField(widget=PhoneNumberPrefixWidget)

    class Meta:
        model = Worker
        fields = ('slack_username', 'phone')
        exclude = ('user', 'start_datetime')


class CommunicationPreferenceForm(forms.ModelForm):
    methods = BitFormField()
    communication_type = forms.IntegerField(required=False)

    class Meta:
        model = CommunicationPreference
        fields = ('methods', 'communication_type')
        exclude = ('worker', 'is_deleted',
                   'created_at')
