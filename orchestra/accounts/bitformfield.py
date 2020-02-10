# flake8: noqa
# Copy pasted from
# https://raw.githubusercontent.com/greyside/django-bitfield/04efae91d292bffb569bd7cc13e5c941e42e8698/bitfield/forms.py
from bitfield.types import BitHandler
from django.forms import CheckboxSelectMultiple
from django.forms import IntegerField
from django.forms import ValidationError
from django.utils.safestring import mark_safe

try:
    from django.utils.encoding import force_text
except ImportError:
    from django.utils.encoding import force_unicode as force_text


class CheckboxSelectMultipleP(CheckboxSelectMultiple):
    # https://djangosnippets.org/snippets/1760/

    def render(self, *args, **kwargs):
        output = super().render(*args, **kwargs)
        return (mark_safe(output.replace(u'<ul>', u'').
                          replace(u'</ul>', u'').
                          replace(u'<li>', u'<p>').
                          replace(u'</li>', u'</p>')))


class BitFieldCheckboxSelectMultiple(CheckboxSelectMultipleP):

    def render(self, name, value, attrs=None, renderer=None):
        if isinstance(value, BitHandler):
            value = [k for k, v in value if v]
        return super().render(name, value, attrs=attrs)

    def _has_changed(self, initial, data):
        if initial is None:
            initial = []
        if data is None:
            data = []
        if initial != data:
            return True
        initial_set = set([force_text(value) for value in initial])
        data_set = set([force_text(value) for value in data])
        return data_set != initial_set


class BitFormField(IntegerField):

    def __init__(self,
                 choices=(),
                 widget_choices=(),
                 widget=BitFieldCheckboxSelectMultiple,
                 *args,
                 **kwargs):
        initial = kwargs.get('initial')
        if isinstance(initial, int):
            l = []
            for i in range(0, 63):
                if (1 << i) & initial > 0:
                    l += [choices[i][0]]
            kwargs['initial'] = l
        self.widget = widget
        super(BitFormField, self).__init__(widget=widget, *args, **kwargs)
        self.choices = choices
        # widget choices is a subset of choices that are available
        self.widget.choices = widget_choices or choices

    def clean(self, value):
        if not value:
            return 0

        # Assume an iterable which contains an item per flag that's enabled
        result = BitHandler(0, [k for k, v in self.choices])
        for k in value:
            try:
                setattr(result, str(k), True)
            except AttributeError:
                raise ValidationError('Unknown choice: %r' % (k,))
        return int(result)
