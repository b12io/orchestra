from orchestra.workflow import Step
from orchestra.workflow import Workflow

from simple_workflow.crawl import crawl_page

crawl_step = Step(
    slug='crawl',
    name='Web Crawling',
    description='Find an awesome image on a website',
    worker_type=Step.WorkerType.MACHINE,
    creation_depends_on=[],
    function=crawl_page,
)

rate_step = Step(
    slug='rate',
    name='Image Rating',
    description='Rate the image that we found',
    worker_type=Step.WorkerType.HUMAN,
    creation_depends_on=[crawl_step],
    required_certifications=[],
    review_policy={'policy': 'no_review'},
    user_interface={
        'javascript_includes': [
            '/static/simple_workflow/rate/js/modules.js',
            '/static/simple_workflow/rate/js/controllers.js',
            '/static/simple_workflow/rate/js/directives.js',
        ],
        'stylesheet_includes': [],
        'angular_module': 'simple_workflow.rate.module',
        'angular_directive': 'rate',
    }
)

simple_workflow = Workflow(
    slug='simple_workflow',
    name='Simple Workflow',
    description='Crawl a web page for an image and rate it'
)

simple_workflow.add_step(crawl_step)
simple_workflow.add_step(rate_step)
