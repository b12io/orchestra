from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.generic import View
from registration.models import RegistrationProfile
from registration.views import RegistrationView

from orchestra.accounts.forms import UserForm
from orchestra.accounts.forms import WorkerForm
from orchestra.accounts import signals
from orchestra.models import Worker

UserModel = get_user_model()


class OrchestraRegistrationView(RegistrationView):
    SEND_ACTIVATION_EMAIL = getattr(settings, 'SEND_ACTIVATION_EMAIL', True)
    success_url = 'registration_complete'

    def register(self, form):
        """
        Given a username, email address and password, register a new
        user account, which will initially be inactive.
        Along with the new ``User`` object, a new
        ``registration.models.RegistrationProfile`` will be created,
        tied to that ``User``, containing the activation key which
        will be used for this account.
        An email will be sent to the supplied email address; this
        email should contain an activation link. The email will be
        rendered using two templates. See the documentation for
        ``RegistrationProfile.send_activation_email()`` for
        information about these templates and the contexts provided to
        them.
        After the ``User`` and ``RegistrationProfile`` are created and
        the activation email is sent, the signal
        ``orchestra.signals.orchestra_user_registered`` will be sent,
        with the new ``User`` as the keyword argument ``user`` and the
        class of this backend as the sender.
        """
        site = get_current_site(self.request)

        if hasattr(form, 'save'):
            new_user_instance = form.save()
        else:
            new_user_instance = (UserModel().objects
                                 .create_user(**form.cleaned_data))

        new_user = RegistrationProfile.objects.create_inactive_user(
            new_user=new_user_instance,
            site=site,
            send_email=self.SEND_ACTIVATION_EMAIL,
            request=self.request,
        )

        # We send our own custom signal here so we don't conflict with anyone
        # using the django-registration project
        signals.orchestra_user_registered.send(sender=self.__class__,
                                               user=new_user,
                                               request=self.request)
        return new_user


@method_decorator(login_required, name='dispatch')
class AccountSettingsView(View):
    template_name = 'accounts/settings.html'
    user_form = UserForm
    worker_form = WorkerForm

    def dispatch(self, request, *args, **kwargs):
        self.worker = Worker.objects.get(user=request.user)
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        user_form = self.user_form(
            instance=request.user)
        worker_form = self.worker_form(instance=self.worker)

        return render(request, self.template_name, {
            'user_form': user_form,
            'worker_form': worker_form,
        })

    def post(self, request, *args, **kwargs):
        user_form = self.user_form(
            data=request.POST, instance=request.user)
        worker_form = self.worker_form(
            data=request.POST, instance=self.worker)

        success = user_form.is_valid() and worker_form.is_valid()
        if success:
            user_form.save()
            worker_form.save()

        return render(request, self.template_name, {
            'user_form': user_form,
            'worker_form': worker_form,
            'success': success,
        })
