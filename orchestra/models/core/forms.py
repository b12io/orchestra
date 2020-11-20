from django.conf import settings
from django.forms import FloatField
from django.forms import ModelForm

from orchestra.models import WorkerAvailability


class DailyAvailabilityField(FloatField):
    def __init__(self, *args, **kwargs):
        max_value = settings.ORCHESTRA_MAX_AUTOSTAFF_HOURS_PER_DAY
        super().__init__(*args, min_value=0, max_value=max_value, **kwargs)


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
        field_classes = {field: DailyAvailabilityField for field in fields}
