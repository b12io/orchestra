from django import forms
from django.contrib.auth import get_user_model
from phonenumber_field.formfields import PhoneNumberField
from phonenumber_field.widgets import PhoneNumberPrefixWidget

from orchestra.accounts.bitformfield import BitFormField
from orchestra.communication.slack import get_slack_user_id
from orchestra.models import CommunicationPreference
from orchestra.models import Worker
from orchestra.models import WorkerAvailability


UserModel = get_user_model()


class UserForm(forms.ModelForm):
    first_name = forms.CharField()
    last_name = forms.CharField()

    class Meta:
        model = UserModel
        fields = ('first_name', 'last_name')
        # TODO(joshblum): support change email
        exclude = ('is_staff', 'is_active', 'date_joined', 'username', 'email')


class DailyAvailabilityField(forms.FloatField):
    def __init__(self, *args, **kwargs):
        max_value = 24  # only 24 hours in a day!
        super().__init__(*args, min_value=0, max_value=max_value, **kwargs)


class WorkerAvailabilityForm(forms.ModelForm):
    class Meta:
        model = WorkerAvailability
        fields = (
            'hours_available_mon',
            'hours_available_tues',
            'hours_available_wed',
            'hours_available_thurs',
            'hours_available_fri',
            'hours_available_sat',
            'hours_available_sun',
        )
        field_classes = {field: DailyAvailabilityField for field in fields}


class WorkerForm(forms.ModelForm):
    slack_username = forms.CharField()
    phone = PhoneNumberField(
        widget=PhoneNumberPrefixWidget(initial='US'))

    class Meta:
        model = Worker
        fields = ('slack_username', 'phone')
        exclude = ('user', 'start_datetime', 'slack_user_id')

    def clean_slack_username(self):
        slack_username = self.cleaned_data.get('slack_username')
        if slack_username:
            slack_user_id = get_slack_user_id(slack_username)
            if slack_user_id is None:
                raise forms.ValidationError(
                    'Incorrect slack username provided')
            self.cleaned_data['slack_user_id'] = slack_user_id
        return self.cleaned_data['slack_username']

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.slack_user_id = self.cleaned_data.get('slack_user_id')
        if commit:
            instance.save()
        return instance


class CommunicationPreferenceForm(forms.ModelForm):
    methods = BitFormField()

    class Meta:
        model = CommunicationPreference
        fields = ('methods',)
        exclude = ('worker', 'is_deleted',
                   'created_at')
