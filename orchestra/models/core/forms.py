from django.forms import ModelForm
from orchestra.models import WorkerAvailability


class WorkerAvailabilityForm(ModelForm):
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
