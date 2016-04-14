from django.db import models
from django.utils import timezone


class DeleteMixin(object):

    def delete(self, *args, **kwargs):
        self.is_deleted = True
        self.save()


class BaseModel(DeleteMixin, models.Model):
    """
    Abstract base class models which defines created_at and is_deleted fields.

    Attributes:
        created_at (datetime.datetime):
            Datetime at which the model is created.
        is_deleted (boolean):
            If value is True, TimeEntry is deleted. Default is False.
    """
    created_at = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True
