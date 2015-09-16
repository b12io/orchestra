from importlib import import_module

from django.conf import settings

from orchestra.core.errors import InvalidSlugValue
from orchestra.core.errors import SlugUniquenessError


class Workflow():

    def __init__(self,
                 **kwargs):
        self.slug = kwargs.get('slug')
        if len(self.slug) > 200:
            raise InvalidSlugValue('Slug value should be less than 200 chars')
        self.name = kwargs.get('name')
        self.description = kwargs.get('description')
        self.steps = {}

    def add_step(self,
                 step):
        if len(step.slug) > 200:
            raise InvalidSlugValue('Slug value should be less than 200 chars')

        if step.slug in self.steps:
            raise SlugUniquenessError('Slug value already taken')

        self.steps[step.slug] = step

    def get_steps(self):
        return self.steps.values()

    def get_step_slugs(self):
        return self.steps.keys()

    def get_step(self, slug):
        return self.steps[slug]

    def get_human_steps(self):
        return [step for slug, step in self.steps.items()
                if step.worker_type == Step.WorkerType.HUMAN]

    def __str__(self):
        return self.slug

    def __unicode__(self):
        return self.slug


class Step():
    class WorkerType:
        HUMAN = 0
        MACHINE = 1

    def __init__(self,
                 **kwargs):
        self.slug = kwargs.get('slug')
        self.name = kwargs.get('name')
        self.description = kwargs.get('description')
        self.worker_type = kwargs.get('worker_type')
        self.creation_depends_on = kwargs.get('creation_depends_on') or []
        self.submission_depends_on = kwargs.get('submission_depends_on') or []
        self.function = kwargs.get('function')
        self.required_certifications = kwargs.get(
            'required_certifications') or []

        # Example: {'policy': 'previously_completed_steps', 'step': ['design']}
        self.assignment_policy = (kwargs.get('assignment_policy')
                                  or get_default_policy(self.worker_type,
                                                        'assignment_policy'))

        # Example: {'policy': 'sampled_review', 'rate': .25, 'max_reviews': 2}
        self.review_policy = (kwargs.get('review_policy')
                              or get_default_policy(self.worker_type,
                                                    'review_policy'))

        # Example: {'html_blob': 'http://some_url',
        #           'javascript_includes': [url1, url2],
        #           'css_includes': [url1, url2]}
        self.user_interface = kwargs.get('user_interface') or {}

    def __str__(self):
        return self.slug

    def __unicode__(self):
        return self.slug


def get_workflows():
    workflows = {}
    for backend_module, variable in settings.ORCHESTRA_PATHS:
        backend_module = import_module(backend_module)
        workflow = getattr(backend_module, variable)
        if workflow.slug in workflows:
            raise SlugUniquenessError('Repeated slug value for workflows.')
        workflows[workflow.slug] = workflow
    return workflows


def get_workflow_by_slug(slug):
    return get_workflows()[slug]


def get_workflow_choices():
    workflows = get_workflows()
    choices = []
    for slug, workflow in workflows.items():
        choices.append((slug, workflow.name))
    return tuple(choices)


def get_step_choices():
    choices = []
    for slug, workflow in iter(get_workflows().items()):
        for step in workflow.get_steps():
            choices.append((step.slug, step.name))
    return tuple(choices)


def get_default_policy(worker_type, policy_name):
    """
    Resets the given policy to its default value.
    """
    default_policies = {
        'assignment_policy': {'policy': 'anyone_certified'},
        'review_policy': {'policy': 'sampled_review',
                          'rate': 1,
                          'max_reviews': 1}
    }
    if worker_type == Step.WorkerType.HUMAN:
        return default_policies[policy_name]
    else:
        return {}
