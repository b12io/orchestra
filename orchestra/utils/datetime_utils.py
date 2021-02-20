from datetime import timedelta
from django.utils import timezone


def first_day_of_the_week(relative_to_date=None):
    if relative_to_date is None:
        relative_to_date = timezone.now()
    return (relative_to_date -
            timedelta(days=relative_to_date.weekday())).date()
