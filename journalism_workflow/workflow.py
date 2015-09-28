from orchestra.workflow import Step
from orchestra.workflow import Workflow

from journalism_workflow.adjust_photos import autoadjust_photos
from journalism_workflow.documents import create_documents

# Instantiate our workflow
journalism_workflow = Workflow(
    slug='journalism',
    name='Journalism Workflow',
    description='Create polished newspaper articles from scratch.',
)

# Zeroth step: we autocreate subfolders and documents we'll need.
document_creation = Step(
    slug='document_creation',
    name='Document Creation',
    description='Create google documents for project in relevant folder.',
    worker_type=Step.WorkerType.MACHINE,
    creation_depends_on=[],
    function=create_documents,
)
journalism_workflow.add_step(document_creation)

# First step: an editor plans out the high-level story idea.
editor_step = Step(
    slug='article_planning',
    name='Article Planning',
    description='Plan out the high-level idea for the story',
    worker_type=Step.WorkerType.HUMAN,
    creation_depends_on=[document_creation],
    required_certifications=['editor'],
    user_interface={
        'javascript_includes': [
            '/static/journalism_workflow/editor/js/modules.js',
            '/static/journalism_workflow/editor/js/controllers.js',
            '/static/journalism_workflow/editor/js/directives.js',
        ],
        'stylesheet_includes': [],
        'angular_module': 'journalism_workflow.editor.module',
        'angular_directive': 'editor',
    },
    review_policy={'policy': 'no_review'},
)
journalism_workflow.add_step(editor_step)

# Then, a reporter researches and drafts an article based on the idea.
reporter_step = Step(
    slug='reporting',
    name='Reporting',
    description='Research and draft the article text',
    worker_type=Step.WorkerType.HUMAN,
    creation_depends_on=[editor_step],
    required_certifications=['reporter'],
    user_interface={
        'javascript_includes': [
            '/static/journalism_workflow/reporter/js/modules.js',
            '/static/journalism_workflow/reporter/js/controllers.js',
            '/static/journalism_workflow/reporter/js/directives.js',
        ],
        'stylesheet_includes': [],
        'angular_module': 'journalism_workflow.reporter.module',
        'angular_directive': 'reporter',
    },

    # A senior reporter should review the article text.
    review_policy={
        'policy': 'sampled_review',
        'rate': 1,        # review all tasks
        'max_reviews': 1  # exactly once
    },
)
journalism_workflow.add_step(reporter_step)

# In parallel, a photographer takes photos that will support the story.
photographer_step = Step(
    slug='photography',
    name='Photography',
    description='Take and edit photos to accompany the article.',
    worker_type=Step.WorkerType.HUMAN,
    creation_depends_on=[editor_step],
    required_certifications=['photographer'],
    user_interface={
        'javascript_includes': [
            '/static/journalism_workflow/photographer/js/modules.js',
            '/static/journalism_workflow/photographer/js/controllers.js',
            '/static/journalism_workflow/photographer/js/directives.js',
        ],
        'stylesheet_includes': [],
        'angular_module': 'journalism_workflow.photographer.module',
        'angular_directive': 'photographer',
    },

    # An experienced photographer should review the photos.
    review_policy={
        'policy': 'sampled_review',
        'rate': 1,        # review all tasks
        'max_reviews': 1  # exactly once
    },
)
journalism_workflow.add_step(photographer_step)

# The photos are automatically adjusted to fit the desired print format.
photo_adjustment_step = Step(
    slug='photo_adjustment',
    name='Photo Adjustment',
    description='Automatically crop and rescale images',
    worker_type=Step.WorkerType.MACHINE,
    creation_depends_on=[photographer_step],
    function=autoadjust_photos,
)
journalism_workflow.add_step(photo_adjustment_step)

# Finally, a copy editor generates a headline and captions the photos.
copy_editor_step = Step(
    slug='copy_editing',
    name='Copy Editing',
    description='caption photos and generate a headline for the story.',
    worker_type=Step.WorkerType.HUMAN,
    creation_depends_on=[photo_adjustment_step, reporter_step],
    required_certifications=['copy_editor'],
    user_interface={
        'javascript_includes': [
            '/static/journalism_workflow/copy_editor/js/modules.js',
            '/static/journalism_workflow/copy_editor/js/controllers.js',
            '/static/journalism_workflow/copy_editor/js/directives.js',
        ],
        'stylesheet_includes': [],
        'angular_module': 'journalism_workflow.copy_editor.module',
        'angular_directive': 'copyEditor',
    },
    review_policy={'policy': 'no_review'},
)
journalism_workflow.add_step(copy_editor_step)
