"""
Settings for the Orchestra app.

Modify these according to your setup, then make sure they are included in your
main settings file by adding::

    from .orchestra_settings import setup_orchestra
    setup_orchestra(__name__)

to the bottom of `settings.py`.
"""

import os
import sys
from datetime import timedelta


def setup_orchestra(settings_module_name):
    settings = sys.modules[settings_module_name]
    if not hasattr(settings, 'INSTALLED_APPS'):
        settings.INSTALLED_APPS = ()
    if not hasattr(settings, 'STATICFILES_FINDERS'):
        settings.STATICFILES_FINDERS = ()

    # General
    ##########

    # URL at which Orchestra is publicly accessible
    settings.ORCHESTRA_URL = 'http://127.0.0.1:8000'

    # Production environment
    environment = os.environ.get('ENVIRONMENT')
    settings.PRODUCTION = False
    settings.STAGING = False
    if environment == 'production':
        settings.PRODUCTION = True
    elif environment == 'staging':
        settings.STAGING = True

    # Required Django apps
    settings.INSTALLED_APPS += (
        'orchestra',
        'beanstalk_dispatch',
        'registration',
        'widget_tweaks',
        'ajax_select',
        'django_object_actions',
    )

    settings.STATICFILES_FINDERS += (
        'django.contrib.staticfiles.finders.FileSystemFinder',
        'django.contrib.staticfiles.finders.AppDirectoriesFinder',
    )

    # Add the Django admin and the Django CMS admin style to make it pretty.
    # The CMS style must be listed before the admin, so we do some processing
    # of the INSTALLED_APPS list to preserve that property.
    settings.INSTALLED_APPS = install_admin(settings.INSTALLED_APPS)

    # Tasks and Workflows
    ######################

    # Installed orchestra workflows to be included as Django apps
    settings.ORCHESTRA_WORKFLOWS = (
        # 'workflows.workflow_app_1',
    )
    settings.INSTALLED_APPS += settings.ORCHESTRA_WORKFLOWS

    # The maximum number of tasks an expert can pick up at a time.
    # Currently disabled.
    settings.ORCHESTRA_MAX_IN_PROGRESS_TASKS = 3

    # The maximum number of tasks to auto-assign to a worker in a single day.
    settings.ORCHESTRA_MAX_AUTOSTAFF_TASKS_PER_DAY = 4

    # S3 bucket name to upload images to
    settings.EDITOR_IMAGE_BUCKET_NAME = 'CHANGEME'

    # Registration
    ###############

    # Orchestra registration urls: must match urls.py
    settings.LOGIN_REDIRECT_URL = '/orchestra/app/'
    settings.LOGIN_URL = '/orchestra/accounts/login/'

    # Orchestra Registration setings
    settings.ACCOUNT_ACTIVATION_DAYS = 7  # One-week activation window
    settings.REGISTRATION_AUTO_LOGIN = True  # Automatically log the user in.
    settings.INCLUDE_REGISTER_URL = False

    # API Authentication
    #####################

    # Orchestra project API client credentials: CHANGE THE SECRET.
    settings.ORCHESTRA_PROJECT_API_KEY = 'orchestra-user'
    settings.ORCHESTRA_PROJECT_API_SECRET = 'CHANGEME'

    # Orchestra project API server authentication via httpsignature.
    settings.INSTALLED_APPS += ('rest_framework_httpsignature',)

    # A dictionary of allowed project API keys and secrets.
    settings.ORCHESTRA_PROJECT_API_CREDENTIALS = {
        'orchestra-user': 'CHANGEME'
    }

    # Django REST framework
    settings.INSTALLED_APPS += ('rest_framework',)

    # Don't authenticate users without a view explicitly calling for it
    settings.REST_FRAMEWORK = {
        'DEFAULT_AUTHENTICATION_CLASSES': (
            'rest_framework.authentication.BasicAuthentication',
            'rest_framework.authentication.SessionAuthentication',
        ),
    }

    # Hijack settings
    settings.INSTALLED_APPS += (
        'hijack',
        'compat',
        'hijack_admin',
        'related_admin',
    )

    # Optionally toggle this to enable user hijack functionality.
    settings.HIJACK_ALLOW_GET_REQUESTS = True

    # Machine Step Scheduling
    ##########################

    # Scheduler for machine steps
    settings.MACHINE_STEP_SCHEDULER = {
        'path': ('orchestra.utils.machine_step_scheduler.'
                 'SynchronousMachineStepScheduler')
    }

    # Beanstalk dispatcher
    # Add keys to use AsynchronousMachineStepScheduler
    settings.BEANSTALK_DISPATCH_SQS_KEY = ''
    settings.BEANSTALK_DISPATCH_SQS_SECRET = ''
    settings.WORK_QUEUE = ''
    if os.environ.get('BEANSTALK_WORKER') == 'True':
        settings.BEANSTALK_DISPATCH_TABLE = {
            'machine_task_executor': ('orchestra.machine_tasks.execute')
        }

    # Email and Notifications
    #########################

    # For registration to work, an email backend must be configured.
    # This file defaults to printing emails to the console if there is no email
    # backend configured already, but that should be changed in production.
    settings.EMAIL_BACKEND = getattr(
        settings,
        'EMAIL_BACKEND',
        'django.core.mail.backends.console.EmailBackend')
    settings.DEFAULT_FROM_EMAIL = getattr(
        settings,
        'DEFAULT_FROM_EMAIL',
        'Orchestra <noreply@example.org>')

    # Notification-specific email for message bundling and searching
    settings.ORCHESTRA_NOTIFICATIONS_FROM_EMAIL = settings.DEFAULT_FROM_EMAIL
    # Feature flag for mocking emails during staffing. Should be disabled for
    # production but enabled otherwise.
    settings.ORCHESTRA_MOCK_EMAILS = False
    # Used to test email sending in development/staging environments
    settings.ORCHESTRA_MOCK_TO_EMAIL = ''

    # 3rd Party Integrations
    #########################

    # AWS Credentials
    settings.AWS_S3_KEY = ''  # FILL IN
    settings.AWS_S3_SECRET = ''  # FILL IN

    # Feature flag for toggling optional Google Apps integration. If a
    # service email and secret key are provided, Google Apps is used to
    # structure project data in Drive folders and can be used for
    # customizing workflow steps as well.
    settings.GOOGLE_APPS = False

    # Optional Google API related service email and path to a secret key.
    settings.GOOGLE_SERVICE_EMAIL = ''
    settings.GOOGLE_P12_PATH = ''

    # Google Drive root folder id in which we create projects.
    settings.GOOGLE_PROJECT_ROOT_ID = ''

    # Feature flags for toggling optional slack integration
    settings.ORCHESTRA_SLACK_INTERNAL_ENABLED = False
    settings.ORCHESTRA_SLACK_EXPERTS_ENABLED = False

    # Settings for slack notifications. Notifications are shared internally
    # upon task status change; the experts team organizes project
    # communication.
    settings.SLACK_EXPERTS_BASE_URL = ''
    settings.SLACK_INTERNAL_API_KEY = ''
    settings.SLACK_EXPERTS_API_KEY = ''
    settings.SLACK_INTERNAL_NOTIFICATION_CHANNEL = '#orchestra-tasks'

    # Settings for orchestra bots Each bot needs a slack token to
    # authenticate the command.
    settings.ORCHESTRA_SLACK_STAFFBOT_TOKEN = ''
    settings.ORCHESTRA_STAFFBOT_WORKER_BATCH_SIZE = 5
    settings.ORCHESTRA_STAFFBOT_BATCH_FREQUENCY = timedelta(minutes=2)
    settings.ORCHESTRA_STAFFBOT_STAFFING_MIN_TIME = timedelta(minutes=30)
    settings.ORCHESTRA_STAFFBOT_STAFFING_GROUP_ID = None

    # Optionally add a path for a template to support third party scripts
    # (such as Google Analytics)
    settings.ORCHESTRA_THIRD_PARTY_SCRIPTS_TEMPLATE = (
        'orchestra/third_party_scripts.html')

    # Optionally configure a google analytics key to learn about your users.
    settings.GOOGLE_ANALYTICS_KEY = ''
    # Pass the Google Analytics key to templates with a context processor.
    install_context_processors(settings)

    # Set to True if you want to block Workers from picking up new
    # tasks while existing ones are returned by reviewers.
    settings.ORCHESTRA_ENFORCE_NO_NEW_TASKS_DURING_REVIEW = True

    # The ID of the Google Drive folder for exporting/importing todo
    # list templates
    settings.ORCHESTRA_TODO_LIST_TEMPLATE_EXPORT_GDRIVE_FOLDER = ''


def install_context_processors(settings):
    try:
        assert (len(settings.TEMPLATES) == 1)
        assert (settings.TEMPLATES[0]['BACKEND'] ==
               'django.template.backends.django.DjangoTemplates')
        settings.TEMPLATES[0]['OPTIONS']['context_processors'].append(
            'orchestra.context_processors.third_party_scripts')
        settings.TEMPLATES[0]['OPTIONS']['context_processors'].append(
            'orchestra.context_processors.google_analytics')
        settings.TEMPLATES[0]['OPTIONS']['context_processors'].append(
            'orchestra.context_processors.base_context')
    except Exception:
        raise ValueError(
            "Expected settings.TEMPLATES to contain a single DjangoTemplates "
            "entry with `['OPTIONS']['context_processors']` in which to "
            "place orchestra context processors. If your template "
            "setup is more complex, please manually add "
            "'orchestra.context_processors.third_party_scripts' and "
            "'orchestra.context_processors.google_analytics' to "
            "the appropriate context processor list.")


def install_admin(installed_apps):
    admin_installed = 'django.contrib.admin' in installed_apps
    cms_installed = 'djangocms_admin_style' in installed_apps

    # If admin but not cms is installed, stick the cms in before it.
    if admin_installed and not cms_installed:
        admin_idx = installed_apps.index('django.contrib.admin')
        new_installed_apps = (
            tuple(installed_apps[:admin_idx]) +
            ('djangocms_admin_style',) +
            tuple(installed_apps[admin_idx:]))

    # If cms but not admin is installed (unlikely!), append the admin.
    elif not admin_installed and cms_installed:
        new_installed_apps = installed_apps + (
            'django.contrib.admin',
        )

    # If neither are installed, append both.
    elif not admin_installed and not cms_installed:
        new_installed_apps = installed_apps + (
            'djangocms_admin_style',
            'django.contrib.admin',
        )

    # If both are installed, do nothing.
    else:
        new_installed_apps = installed_apps

    return new_installed_apps
