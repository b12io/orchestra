from django.conf import settings
from django.forms import FloatField
from django.forms import ModelForm
from django.forms import ValidationError

from orchestra.models import WorkerAvailability


class DailyAvailabilityField(FloatField):
    def validate(self, value):
        super().validate(value)
        max_hours = settings.ORCHESTRA_MAX_AUTOSTAFF_HOURS_PER_DAY
        if value < 0 or value >= max_hours:
            raise ValidationError(
                _('Hours must be between 0 and %(max_hours)s'),
                code='invalid_hours',
                params={'max_hours': max_hours},
            )


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
