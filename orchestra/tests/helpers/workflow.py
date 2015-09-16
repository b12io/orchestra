from orchestra.workflow import Workflow
from orchestra.workflow import Step

step1 = Step(slug='step1',
             name='The first step',
             description='The longer description of the first step',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[],
             required_certifications=['certification1'],
             review_policy={'policy': 'sampled_review',
                            'rate': 1,
                            'max_reviews': 2},
             user_interface={
                 'javascript_includes': ['/path/to/some.js'],
                 'stylesheet_includes': ['/path/to/some.css'],
                 'angular_module': 'step1.module',
                 'angular_directive': 'step1_directive'
             }
             )

step2 = Step(slug='step2',
             name='The second step',
             description='The longer description of the second step',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[step1],
             required_certifications=['certification1',
                                      'certification2'],
             review_policy={'policy': 'sampled_review',
                            'rate': 1,
                            'max_reviews': 1},
             user_interface={
                 'javascript_includes': ['/path/to/some.js'],
                 'stylesheet_includes': ['/path/to/some.css'],
                 'angular_module': 'step2.module',
                 'angular_directive': 'step2_directive'
             }
             )

step3 = Step(slug='step3',
             name='The third step',
             description='The longer description of the third step',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[step2],
             required_certifications=[],
             review_policy={'policy': 'sampled_review',
                            'rate': 1,
                            'max_reviews': 1},
             user_interface={
                 'javascript_includes': ['/path/to/some.js'],
                 'stylesheet_includes': ['/path/to/some.css'],
                 'angular_module': 'step3.module',
                 'angular_directive': 'step3_directive'
             }
             )

workflow = Workflow(slug='test_workflow',
                    name='The workflow',
                    description='A description of the workflow')

workflow.add_step(step1)
workflow.add_step(step2)
workflow.add_step(step3)


step4 = Step(slug='step4',
             name='The step4 for workflow2',
             description='The longer description of the step4 for workflow2',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[],
             required_certifications=[],
             review_policy={'policy': 'sampled_review',
                            'rate': 0,
                            'max_reviews': 0},
             user_interface={
                 'javascript_includes': ['/path/to/some.js'],
                 'stylesheet_includes': ['/path/to/some.css'],
                 'angular_module': 'step4.module',
                 'angular_directive': 'step4_directive'
             }
             )


def simple_json(project_data, dependencies):
    return {'json': 'simple'}

simple_machine = Step(slug='simple_machine',
                      name='Simple machine step',
                      description='This task returns some JSON',
                      worker_type=Step.WorkerType.MACHINE,
                      creation_depends_on=[step4],
                      function=simple_json)

workflow2 = Workflow(slug='test_workflow_2',
                     name='The workflow 2',
                     description='A description of the workflow')
workflow2.add_step(step4)
workflow2.add_step(simple_machine)

# Workflow for testing related task assignment
step_0 = Step(
    slug='step_0',
    name='The first step',
    description='The longer description of the first step',
    worker_type=Step.WorkerType.HUMAN,
    creation_depends_on=[],
    required_certifications=[],
    review_policy={'policy': 'sampled_review',
                   'rate': 1,
                   'max_reviews': 2},
    user_interface={
        'javascript_includes': ['/path/to/some.js'],
        'stylesheet_includes': ['/path/to/some.css'],
        'angular_module': 'step1.module',
        'angular_directive': 'step1_directive'
    }
)

step_1 = Step(
    slug='step_1',
    name='The second step',
    description='The longer description of the second step',
    worker_type=Step.WorkerType.HUMAN,
    creation_depends_on=[step_0],
    required_certifications=['certification2'],
    review_policy={'policy': 'sampled_review',
                   'rate': 1,
                   'max_reviews': 1},
    assignment_policy={'policy': 'previously_completed_steps',
                       'steps': ['step_0']},
    user_interface={
        'javascript_includes': ['/path/to/some.js'],
        'stylesheet_includes': ['/path/to/some.css'],
        'angular_module': 'step2.module',
        'angular_directive': 'step2_directive'
    }
)

assignment_policy_workflow = Workflow(
    slug='assignment_policy_workflow',
    name='The workflow',
    description='A description of the workflow'
)

assignment_policy_workflow.add_step(step_0)
assignment_policy_workflow.add_step(step_1)


# The following is a workflow with a more complex dependency graph to test the
# topographical sort and other graph related functions.
#
# A - C \     / G
#        E - F
# B - D /     \ H
#
# Correct ordering would be:
# [A B] [C D] E F [G H]
# where letters in brackets can go in either order

stepA = Step(slug='stepA',
             name='Step A',
             description='Step A',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[],
             )

stepB = Step(slug='stepB',
             name='Step B',
             description='Step B',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[],
             )

stepC = Step(slug='stepC',
             name='Step C',
             description='Step C',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepA],
             )

stepD = Step(slug='stepD',
             name='Step D',
             description='Step D',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepB],
             )

stepE = Step(slug='stepE',
             name='Step E',
             description='Step E',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepC, stepD],
             )

stepF = Step(slug='stepF',
             name='Step F',
             description='Step F',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepE],
             )

stepG = Step(slug='stepG',
             name='Step G',
             description='Step G',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepF],
             )

stepH = Step(slug='stepH',
             name='Step H',
             description='Step H',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepF],
             )

workflow3 = Workflow(slug='crazy_workflow',
                     name='The crazy workflow',
                     description='A description of the crazy workflow')

workflow3.add_step(stepA)
workflow3.add_step(stepB)
workflow3.add_step(stepC)
workflow3.add_step(stepD)
workflow3.add_step(stepE)
workflow3.add_step(stepF)
workflow3.add_step(stepG)
workflow3.add_step(stepH)


# The following is a workflow that contains a cycle.
stepA = Step(slug='stepA',
             name='Step A',
             description='Step A',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[],
             )

stepB = Step(slug='stepB',
             name='Step B',
             description='Step B',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepA],
             )

stepC = Step(slug='stepC',
             name='Step C',
             description='Step C',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepB],
             )
stepB.creation_depends_on.append(stepC)

workflow4 = Workflow(slug='erroneous_workflow_1',
                     name='Erroneous Workflow 1',
                     description='The workflow is wrong')

workflow4.add_step(stepA)
workflow4.add_step(stepB)
workflow4.add_step(stepC)

# The following is a workflow that references another random step and therefore
# has no starting point
stepA = Step(slug='stepA',
             name='Step A',
             description='Step A',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepB],  # Old definition of stepB!!!
             )

stepB = Step(slug='stepB',
             name='Step B',
             description='Step B',
             worker_type=Step.WorkerType.HUMAN,
             creation_depends_on=[stepA],
             )

workflow5 = Workflow(slug='erroneous_workflow_2',
                     name='Erroneous Workflow 2',
                     description='The workflow is wrong')

workflow5.add_step(stepA)
workflow5.add_step(stepB)
