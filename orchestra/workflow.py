from importlib import import_module

from django.conf import settings

from orchestra.core.errors import InvalidSlugValue
from orchestra.core.errors import SlugUniquenessError


class Workflow():
    """
    Workflows represent execution graphs of human and machine steps.

    Attributes:
        slug (str):
            Unique identifier for the workflow.
        name (str):
            Human-readable name for the workflow.
        description (str):
            A longer description of the workflow.
        steps (dict):
            Steps comprising the workflow.
    """
    def __init__(self,
                 **kwargs):
        self.slug = kwargs.get('slug')
        if len(self.slug) > 200:
            raise InvalidSlugValue('Slug value should be less than 200 chars')
        self.name = kwargs.get('name')
        self.description = kwargs.get('description')
        self.steps = {}

    def add_step(self, step):
        """
        Add `step` to the workflow.

        Args:
            step (orchestra.workflow.Step):
                The step to be added.

        Returns:
            None

        Raises:
            orchestra.core.errors.InvalidSlugValue:
                Step slug should have fewer than 200 characters.
            orchestra.core.errors.SlugUniquenessError:
                Step slug has already been used in this workflow.
        """
        if len(step.slug) > 200:
            raise InvalidSlugValue('Slug value should be less than 200 chars')

        if step.slug in self.steps:
            raise SlugUniquenessError('Slug value already taken')

        self.steps[step.slug] = step

    def get_steps(self):
        """
        Return all steps for the workflow.

        Args:
            None

        Returns:
            steps ([orchestra.workflow.Step]):
                List of steps for the workflow.
        """
        return self.steps.values()

    def get_step_slugs(self):
        """
        Return all step slugs for the workflow.

        Args:
            None

        Returns:
            slugs ([str]):
                List of step slugs for the workflow.
        """
        return self.steps.keys()

    def get_step(self, slug):
        """
        Return the specified step from the workflow.

        Args:
            slug (str):
                The slug of the desired step.

        Returns:
            step (orchestra.workflow.Step):
                The specified step from the workflow.
        """
        return self.steps[slug]

    def get_human_steps(self):
        """
        Return steps from the workflow with a human `worker_type`.

        Args:
            None

        Returns:
            steps ([orchestra.workflow.Step]):
                Steps from the workflow with a human `worker_type`..
        """
        return [step for slug, step in self.steps.items()
                if step.worker_type == Step.WorkerType.HUMAN]

    def __str__(self):
        return self.slug

    def __unicode__(self):
        return self.slug


class Step():
    """
    Steps represent nodes on a workflow execution graph.

    Attributes:
        slug (str):
            Unique identifier for the step.
        name (str):
            Human-readable name for the step.
        description (str):
            A longer description of the step.
        worker_type (orchestra.workflow.Step.WorkerType):
            Indicates whether the policy is for a human or machine.
        creation_depends_on ([str]):
            Slugs for steps on which this step's creation depends.
        submission_depends_on ([str]):
            Slugs for steps on which this step's submission depends.
        function (function):
            Function to execute during step. Should be present only for
            machine tasks
        required_certifications ([str]):
            Slugs for certifications required for a worker to pick up
            tasks based on this step.
    """

    class WorkerType:
        """Specifies whether step is performed by human or machine"""
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
    """
    Return all stored workflows.

    Args:
        None

    Returns:
        workflows ([orchestra.workflow.Workflow]):
            A dict of all workflows keyed by slug.
    """
    workflows = {}
    for backend_module, variable in settings.ORCHESTRA_PATHS:
        backend_module = import_module(backend_module)
        workflow = getattr(backend_module, variable)
        if workflow.slug in workflows:
            raise SlugUniquenessError('Repeated slug value for workflows.')
        workflows[workflow.slug] = workflow
    return workflows


def get_workflow_by_slug(slug):
    """
    Return the workflow specified by `slug`.

    Args:
        slug (str):
            The slug of the desired workflow.

    Returns:
        workflow (orchestra.workflow.Workflow):
            The corresponding workflow object.
    """
    return get_workflows()[slug]


def get_workflow_choices():
    """
    Return workflow data formatted as `choices` for a model field.

    Args:
        None

    Returns:
        workflow_choices (tuple):
            A tuple of tuples containing each workflow slug and
            human-readable name.
    """
    workflows = get_workflows()
    choices = []
    for slug, workflow in workflows.items():
        choices.append((slug, workflow.name))
    return tuple(choices)


def get_step_choices():
    """
    Return step data formatted as `choices` for a model field.

    Args:
        None

    Returns:
        step_choices (tuple):
            A tuple of tuples containing each step slug and
            human-readable name.
    """
    choices = []
    for slug, workflow in iter(get_workflows().items()):
        for step in workflow.get_steps():
            choices.append((step.slug, step.name))
    return tuple(choices)


def get_default_policy(worker_type, policy_name):
    """
    Return the default value for a specified policy.

    Args:
        worker_type (orchestra.workflow.Step.WorkerType):
            Indicates whether the policy is for a human or machine.
        policy_name (str):
            The specified policy identifier.

    Returns:
        default_policy (dict):
            A dict containing the default policy for the worker type and
            policy name specified.
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
