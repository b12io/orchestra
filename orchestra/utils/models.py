from enum import Enum

from django.db import models
from django.db.models import CASCADE
from django.utils import timezone


class DeleteMixin(object):
    """
    Overrides delete and sets `is_deleted=True` instead of deleting object.
    Intended to be used with models that have an `is_deleted` field.
    """

    def delete(self, actually_delete=False, *args, **kwargs):
        # Implement cascading deletes.
        # NOTE(lydia): This ignores any other constraints passed to on_delete.
        if actually_delete:
            return super().delete(*args, **kwargs)
        fields = self._meta.get_fields(include_hidden=True)
        for field in fields:
            # Pass on fields that are not many-to-one relationships.
            if not ((field.one_to_many or field.one_to_one) and
                    field.auto_created):
                continue

            # Check if foreign key is set up with on_delete=CASCADE.
            if field.on_delete != CASCADE:
                continue

            # Query for all related objects and delete them.
            query_args = {field.field.name: self.id}
            related_objs = field.related_model.objects.filter(
                **query_args)
            for obj in related_objs:
                obj.delete()

        # Mark current object as deleted.
        self.is_deleted = True
        self.save()


class BaseModelManager(models.Manager):
    """
    Model manager intended to be used with models with an `is_deleted` field.
    Overrides the initial QuerySet to filter for objects where `is_deleted`
    is false.
    """

    def get_queryset(self):
        return super().get_queryset().filter(is_deleted=False)


class BaseModel(DeleteMixin, models.Model):
    """
    Abstract base class models which defines created_at and is_deleted fields.

    Attributes:
        created_at (datetime.datetime):
            Datetime at which the model is created.
        is_deleted (boolean):
            If value is True, mdoel is deleted. Default is False.
    """
    objects = BaseModelManager()
    unsafe_objects = models.Manager()

    created_at = models.DateTimeField(default=timezone.now)
    is_deleted = models.BooleanField(default=False)

    class Meta:
        abstract = True


class ChoicesEnum(Enum):
    """An enum suitable for use in Django model field choices.

    Allows defining enums using descriptive strings, then automatically assigns
    integer values to them for storage in an `IntegerField.` Example usage:

    >>> class MyEnum(ChoicesEnum):
    ...     item0 = 'My first item'
    ...     item1 = 'My other item'
    ...     blue = 'My third item'
    ...
    >>> class MyModel(models.Model):
    ...     my_field = models.IntegerField(choices=MyEnum.choices())
    ...
    >>> m = MyModel(my_field=MyEnum.blue.value)
    >>> m.my_field
    2
    >>> m.get_my_field_display()
    'My third item'
    """
    def __new__(cls, description):
        """ Assigns 0-indexed values to each enum member on class creation. """
        value = len(cls.__members__)
        obj = object.__new__(cls)
        obj.description = description
        obj._value_ = value
        return obj

    def as_choice(self):
        """ Formats an enum member for use in a Django model field choice. """
        return (self.value, self.description)

    def as_dict(self):
        return {
            'value': self.value,
            'description': self.description
        }

    def __repr__(self):
        return "<{}.{}: {} ({})>".format(
            self.__class__.__name__,
            self.name,
            self.value,
            self.description)

    @classmethod
    def choices(cls):
        """ Formats all enum members for use in Django model field choices.

        Output looks like:
        >>> MyEnum.choices()
        [
            (0, 'My first item'),
            (1, 'My other item'),
            (2, 'My third item'),
        ]

        And it can be used like:
        >>> some_field = IntegerField(choices=MyEnum.choices())

        """
        # Ideally this would be a generator, but Django seems to break when
        # passing choices=<generator> into a model field.
        return [item.as_choice() for item in cls]

    @classmethod
    def serialize(cls):
        """ Formats all enum members for external use (e.g., angular code).

        Output looks like:
        >>> MyEnum.serialize()
        {
            'MY_FIRST_ITEM': {
                'value': 0,
                'description': 'My first name'
            },
            ...
        }
        """
        return {item.name: item.as_dict() for item in cls}
