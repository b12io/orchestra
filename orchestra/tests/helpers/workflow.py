from orchestra.models import Certification
from orchestra.models import Workflow
from orchestra.models import Step
from orchestra.models import WorkflowVersion


# Dummy machine step function so we can test machine step scheduling
def simple_json(project_data, dependencies):
    return {'json': 'simple'}


def machine_task_function():
    pass


workflow_fixtures = [
    {
        'slug': 'w1',
        'name': 'Workflow One',
        'certifications': [
            {
                'slug': 'certification1',
                'name': 'The first certification',
                'required_certifications': []
            },
            {
                'slug': 'certification2',
                'name': 'The second certification',
                'required_certifications': ['certification1']
            },
        ],
        'versions': [
            {
                'slug': 'test_workflow',
                'name': 'The workflow',
                'description': 'A description of the workflow',
                'steps': [
                    {
                        'slug': 'step1',
                        'name': 'The first step',
                        'description': ('The longer description of the '
                                        'first step'),
                        'is_human': True,
                        'creation_depends_on': [],
                        'required_certifications': ['certification1'],
                        'review_policy': {
                            'policy': 'sampled_review',
                            'rate': 1,
                            'max_reviews': 2,
                        },
                        'user_interface': {
                            'javascript_includes': ['/path/to/some.js'],
                            'stylesheet_includes': ['/path/to/some.css'],
                            'angular_module': 'step1',
                            'angular_directive': 'step1_directive',
                        },
                    },
                    {
                        'slug': 'step2',
                        'name': 'The second step',
                        'description': ('The longer description of the '
                                        'second step'),
                        'is_human': True,
                        'creation_depends_on': ['step1'],
                        'required_certifications': [
                            'certification1',
                            'certification2',
                        ],
                        'review_policy': {
                            'policy': 'sampled_review',
                            'rate': 1,
                            'max_reviews': 1,
                        },
                        'user_interface': {
                            'javascript_includes': ['/path/to/some.js'],
                            'stylesheet_includes': ['/path/to/some.css'],
                            'angular_module': 'step2',
                            'angular_directive': 'step2_directive',
                        },
                    },
                    {
                        'slug': 'step3',
                        'name': 'The third step',
                        'description': ('The longer description of the '
                                        'third step'),
                        'is_human': True,
                        'creation_depends_on': ['step2'],
                        'required_certifications': [],
                        'review_policy': {
                            'policy': 'sampled_review',
                            'rate': 1,
                            'max_reviews': 1,
                        },
                        'user_interface': {
                            'javascript_includes': ['/path/to/some.js'],
                            'stylesheet_includes': ['/path/to/some.css'],
                            'angular_module': 'step3',
                            'angular_directive': 'step3_directive',
                        },
                    },
                ],
            },
        ],
    },
    {
        'slug': 'w2',
        'name': 'Workflow 2',
        'versions': [
            {
                'slug': 'test_workflow_2',
                'name': 'The workflow 2',
                'description': 'A description of the workflow',
                'steps': [
                    {
                        'slug': 'step4',
                        'name': 'The step4 for workflow2',
                        'description': ('The longer description of the '
                                        'step4 for workflow2'),
                        'is_human': True,
                        'creation_depends_on': [],
                        'required_certifications': [],
                        'review_policy': {
                            'policy': 'sampled_review',
                            'rate': 0,
                            'max_reviews': 0,
                        },
                        'user_interface': {
                            'javascript_includes': ['/path/to/some.js'],
                            'stylesheet_includes': ['/path/to/some.css'],
                            'angular_module': 'step4',
                            'angular_directive': 'step4_directive',
                        },
                    },
                    {
                        'slug': 'simple_machine',
                        'name': 'Simple machine step',
                        'description': 'This task returns some JSON',
                        'is_human': False,
                        'creation_depends_on': ['step4'],
                        'execution_function': {
                            'path': ('orchestra.tests.helpers.'
                                     'workflow.simple_json')
                        },
                    },
                ],
            },
        ],
    },
    {
        'slug': 'assignment_policy',
        'name': 'Assignment Policy Workflow',
        'certifications': [
            {
                'slug': 'certification1_ap',
                'name': 'The first certification',
                'required_certifications': []
            },
            {
                'slug': 'certification2_ap',
                'name': 'The second certification',
                'required_certifications': ['certification1']
            },
        ],
        'versions': [
            {
                'slug': 'assignment_policy_workflow',
                'name': 'The workflow',
                'description': 'A description of the workflow',
                'steps': [
                    {
                        'slug': 'step_0',
                        'name': 'The first step',
                        'description': ('The longer description of the '
                                        'first step'),
                        'is_human': True,
                        'creation_depends_on': [],
                        'required_certifications': [],
                        'review_policy': {
                            'policy': 'sampled_review',
                            'rate': 1,
                            'max_reviews': 2,
                        },
                        'user_interface': {
                            'javascript_includes': ['/path/to/some.js'],
                            'stylesheet_includes': ['/path/to/some.css'],
                            'angular_module': 'step1',
                            'angular_directive': 'step1_directive',
                        },
                    },
                    {
                        'slug': 'step_1',
                        'name': 'The second step',
                        'description': ('The longer description of the '
                                        'second step'),
                        'is_human': True,
                        'creation_depends_on': ['step_0'],
                        'required_certifications': ['certification2_ap'],
                        'review_policy': {
                            'policy': 'sampled_review',
                            'rate': 1,
                            'max_reviews': 1,
                        },
                        'assignment_policy': {
                            'policy_function': {
                                'entry_level': {
                                    'path': ('orchestra.assignment_policies.'
                                             'previously_completed_steps'),
                                    'kwargs': {

                                        'related_steps': ['step_0'],
                                    }
                                }
                            }
                        },
                        'user_interface': {
                            'javascript_includes': ['/path/to/some.js'],
                            'stylesheet_includes': ['/path/to/some.css'],
                            'angular_module': 'step2',
                            'angular_directive': 'step2_directive',
                        },
                    },
                ],
            },
        ],
    },
    {
        'slug': 'staffbot_assignment_policy',
        'name': 'StaffBot Assignment Policy Workflow',
        'versions': [
            {
                'slug': 'staffbot_assignment_policy_workflow',
                'name': 'The workflow',
                'description': 'A description of the workflow',
                'steps': [
                    {
                        'slug': 'staffbot_step_0',
                        'name': 'The first step',
                        'description': ('The longer description of the '
                                        'first step'),
                        'detailed_description_function': {
                            'path': ('orchestra.tests.helpers.'
                                     'fixtures.get_detailed_description')
                        },
                        'is_human': True,
                        'creation_depends_on': [],
                        'required_certifications': [],
                        'review_policy': {
                            'policy': 'no_review',
                        },
                        'assignment_policy': {
                            'policy_function': {
                                'entry_level': {
                                    'path': ('orchestra.bots.'
                                             'assignment_policies.'
                                             'staffbot_autoassign'),
                                }
                            }
                        },
                        'user_interface': {
                            'javascript_includes': ['/path/to/some.js'],
                            'stylesheet_includes': ['/path/to/some.css'],
                            'angular_module': 'step1',
                            'angular_directive': 'step1_directive',
                        },
                    },
                    {
                        'slug': 'staffbot_step_1',
                        'name': 'The second step',
                        'description': ('The longer description of the '
                                        'second step'),
                        'detailed_description_function': {
                            'path': ('orchestra.tests.helpers.'
                                     'fixtures.get_detailed_description'),
                            'kwargs': {
                                'text': 'step 2 text',
                            },
                        },
                        'is_human': True,
                        'creation_depends_on': ['staffbot_step_0'],
                        'required_certifications': ['certification2_ap'],
                        'review_policy': {
                            'policy': 'sampled_review',
                            'rate': 1,
                            'max_reviews': 1,
                        },
                        'assignment_policy': {
                            'policy_function': {
                                'entry_level': {
                                    'path': ('orchestra.bots.'
                                             'assignment_policies.'
                                             'staffbot_autoassign'),
                                    'kwargs': {

                                        'related_steps': ['staffbot_step_0'],
                                    }
                                }
                            }
                        },
                        'user_interface': {
                            'javascript_includes': ['/path/to/some.js'],
                            'stylesheet_includes': ['/path/to/some.css'],
                            'angular_module': 'step2',
                            'angular_directive': 'step2_directive',
                        },
                    },
                ],
            },
        ],
    },

    # The following is a workflow with a more complex dependency graph to test
    # the topographical sort and other graph related functions.
    #
    # A - C \     / G
    #        E - F
    # B - D /     \ H
    #
    # Correct ordering would be:
    # [A B] [C D] E F [G H]
    # where letters in brackets can go in either order
    {
        'slug': 'w3',
        'name': 'Workflow 3',
        'versions': [
            {
                'slug': 'crazy_workflow',
                'name': 'The crazy workflow',
                'description': 'A description of the crazy workflow',
                'steps': [
                    {
                        'slug': 'stepA',
                        'name': 'Step A',
                        'description': 'Step A',
                        'is_human': True,
                        'creation_depends_on': [],
                    },
                    {
                        'slug': 'stepB',
                        'name': 'Step B',
                        'description': 'Step B',
                        'is_human': True,
                        'creation_depends_on': [],
                    },
                    {
                        'slug': 'stepC',
                        'name': 'Step C',
                        'description': 'Step C',
                        'is_human': True,
                        'creation_depends_on': ['stepA'],
                    },
                    {
                        'slug': 'stepD',
                        'name': 'Step D',
                        'description': 'Step D',
                        'is_human': True,
                        'creation_depends_on': ['stepB'],
                    },
                    {
                        'slug': 'stepE',
                        'name': 'Step E',
                        'description': 'Step E',
                        'is_human': True,
                        'creation_depends_on': ['stepC', 'stepD'],
                    },
                    {
                        'slug': 'stepF',
                        'name': 'Step F',
                        'description': 'Step F',
                        'is_human': True,
                        'creation_depends_on': ['stepE'],
                    },
                    {
                        'slug': 'stepG',
                        'name': 'Step G',
                        'description': 'Step G',
                        'is_human': True,
                        'creation_depends_on': ['stepF'],
                    },
                    {
                        'slug': 'stepH',
                        'name': 'Step H',
                        'description': 'Step H',
                        'is_human': True,
                        'creation_depends_on': ['stepF'],
                    },
                ],
            },
        ],
    },

    # The following is a workflow that contains a cycle.
    {
        'slug': 'w4',
        'name': 'Workflow 4',
        'versions': [
            {
                'slug': 'erroneous_workflow_1',
                'name': 'Erroneous Workflow 1',
                'description': 'The workflow is wrong',
                'steps': [
                    {
                        'slug': 'stepA',
                        'name': 'Step A',
                        'description': 'Step A',
                        'is_human': True,
                        'creation_depends_on': [],
                    },
                    {
                        'slug': 'stepB',
                        'name': 'Step B',
                        'description': 'Step B',
                        'is_human': True,
                        'creation_depends_on': ['stepA', 'stepC'],
                    },
                    {
                        'slug': 'stepC',
                        'name': 'Step C',
                        'description': 'Step C',
                        'is_human': True,
                        'creation_depends_on': ['stepB'],
                    },
                ],
            },
        ],
    },

    # The following is a workflow that has no starting point (and also a
    # cycle).
    {
        'slug': 'w5',
        'name': 'Workflow 5',
        'versions': [
            {
                'slug': 'erroneous_workflow_2',
                'name': 'Erroneous Workflow 2',
                'description': 'The workflow is wrong',
                'steps': [
                    {
                        'slug': 'stepA',
                        'name': 'Step A',
                        'description': 'Step A',
                        'is_human': True,
                        'creation_depends_on': ['stepB'],
                    },
                    {
                        'slug': 'stepB',
                        'name': 'Step B',
                        'description': 'Step B',
                        'is_human': True,
                        'creation_depends_on': ['stepA'],
                    },
                ],
            },
        ],
    },

    # The following is a workflow with a single machine step.
    {
        'slug': 'machine_workflow',
        'name': 'Machine workflow',
        'versions': [
            {
                'slug': 'machine_workflow_version',
                'name': 'v1',
                'description': 'A workflow with a single machine step',
                'steps': [
                    {
                        'slug': 'machine_step',
                        'name': 'Machine step',
                        'description': 'A step to be carried out by a machine',
                        'is_human': False,
                        'creation_depends_on': [],
                        'required_certifications': [],
                        'execution_function': {},
                    },
                ],
            },
        ],
    },
]


def assert_test_dir_workflow_not_loaded(test_case):
    """ Verify that the test_dir workflow's DB objects don't exist. """
    test_case.assertModelInstanceNotExists(Workflow, {'slug': 'test_dir'})
    test_case.assertModelInstanceNotExists(Certification, {
        'slug': 'certification1',
        'workflow__slug': 'test_dir',
    })
    test_case.assertModelInstanceNotExists(Certification, {
        'slug': 'certification2',
        'workflow__slug': 'test_dir',
    })


def assert_test_dir_workflow_loaded(test_case):
    """ Verify that the test_dir workflow's DB objects exist. """
    workflow = test_case.assertModelInstanceExists(
        Workflow,
        {
            'slug': 'test_dir',
        },
        {
            'name': 'Test Workflow',
            'description': 'Test workflow functionality.',
        })

    certification1 = test_case.assertModelInstanceExists(
        Certification,
        {
            'workflow': workflow,
            'slug': 'certification1',
        },
        {
            'name': 'First Certification',
            'description': 'The first one',
        })
    test_case.assertEqual(list(certification1.required_certifications.all()),
                          [])

    certification2 = test_case.assertModelInstanceExists(
        Certification,
        {
            'workflow': workflow,
            'slug': 'certification2',
        },
        {
            'name': 'Second Certification',
            'description': 'The second one',
        })
    test_case.assertEqual(list(certification2.required_certifications.all()),
                          [certification1])


def assert_test_dir_v1_not_loaded(test_case):
    """ Verify that the test_dir workflow v1's DB objects don't exist. """
    test_case.assertModelInstanceNotExists(WorkflowVersion, {
        'slug': 'test_v1',
        'workflow__slug': 'test_dir',
    })
    test_case.assertModelInstanceNotExists(Step, {
        'slug': 's1',
        'workflow_version__slug': 'test_v1',
    })
    test_case.assertModelInstanceNotExists(Step, {
        'slug': 's2',
        'workflow_version__slug': 'test_v1',
    })
    test_case.assertModelInstanceNotExists(Step, {
        'slug': 's3',
        'workflow_version__slug': 'test_v1',
    })


def assert_test_dir_v1_loaded(test_case):
    """ Verify that the test_dir workflow v1's DB objects exist. """
    version1 = test_case.assertModelInstanceExists(
        WorkflowVersion,
        {
            'workflow__slug': 'test_dir',
            'slug': 'test_v1',
        },
        {
            'name': 'Test Workflow v1',
            'description': 'First test workflow version',
        })

    step1 = test_case.assertModelInstanceExists(
        Step,
        {
            'workflow_version': version1,
            'slug': 's1',
        },
        {
            'name': 'Step 1',
            'description': 'The first step',
            'detailed_description_function': {
                'path': ('orchestra.tests.helpers.'
                         'fixtures.get_detailed_description'),
                'kwargs': {
                    'text': 'step 2 text'
                }
            },
            'is_human': False,
            'execution_function': {
                'path': 'v1.machine.machine_function',
            },
            'review_policy': {},
            'user_interface': {},
        })
    test_case.assertEqual(list(step1.required_certifications.all()), [])
    test_case.assertEqual(list(step1.creation_depends_on.all()), [])
    test_case.assertEqual(list(step1.submission_depends_on.all()), [])

    step2 = test_case.assertModelInstanceExists(
        Step,
        {
            'workflow_version': version1,
            'slug': 's2',
        },
        {
            'name': 'Step 2',
            'description': 'The second step',
            'is_human': True,
            'execution_function': {},
            'review_policy': {
                'policy': 'no_review',
            },
            'user_interface': {
                'angular_module': 'test_dir.v1.s2',
                'angular_directive': 's2',
                'javascript_includes': [
                    'test_dir/v1/s2/js/modules.js',
                    'test_dir/v1/s2/js/controllers.js',
                    'test_dir/v1/s2/js/directives.js',
                ],
            },
        })
    test_case.assertEqual(list(step2.required_certifications.all()),
                          [Certification.objects.get(
                              slug='certification1',
                              workflow__slug='test_dir',
                          )])
    test_case.assertEqual(list(step2.creation_depends_on.all()), [step1])
    test_case.assertEqual(list(step2.submission_depends_on.all()), [])

    step3 = test_case.assertModelInstanceExists(
        Step,
        {
            'workflow_version': version1,
            'slug': 's3',
        },
        {
            'name': 'Step 3',
            'description': 'The third step',
            'is_human': True,
            'execution_function': {},
            'review_policy': {
                'policy': 'sampled_review',
                'rate': 1,
                'max_reviews': 1,
            },
            'user_interface': {
                'angular_module': 'test_dir.v1.s3',
                'angular_directive': 's3',
                'javascript_includes': [
                    'test_dir/v1/s3/js/modules.js',
                    'test_dir/v1/s3/js/controllers.js',
                    'test_dir/v1/s3/js/directives.js',
                ],
            },
        })
    test_case.assertEqual(set(step3.required_certifications.all()),
                          set(Certification.objects.filter(
                              slug__in=['certification1', 'certification2'],
                              workflow__slug='test_dir',
                          )))
    test_case.assertEqual(list(step3.creation_depends_on.all()), [step1])
    test_case.assertEqual(list(step3.submission_depends_on.all()), [step2])


def assert_test_dir_v2_not_loaded(test_case):
    """ Verify that the test_dir workflow v2's DB objects exist. """
    test_case.assertModelInstanceNotExists(WorkflowVersion, {
        'slug': 'test_v2',
        'workflow__slug': 'test_dir',
    })
    test_case.assertModelInstanceNotExists(Step, {
        'slug': 's1',
        'workflow_version__slug': 'test_v2',
    })
    test_case.assertModelInstanceNotExists(Step, {
        'slug': 's2',
        'workflow_version__slug': 'test_v2',
    })


def assert_test_dir_v2_loaded(test_case):
    """ Verify that the test_dir workflow v2's DB objects exist. """
    version2 = test_case.assertModelInstanceExists(
        WorkflowVersion,
        {
            'workflow__slug': 'test_dir',
            'slug': 'test_v2',
        },
        {
            'name': 'Test Workflow V2',
            'description': 'Second test workflow version',
        })

    step1 = test_case.assertModelInstanceExists(
        Step,
        {
            'workflow_version': version2,
            'slug': 's1',
        },
        {
            'name': 'Step 1',
            'description': 'The first step.',
            'is_human': False,
            'execution_function': {
                'path': 'v2.machine.machine_function'
            },
            'review_policy': {},
            'user_interface': {},
        })
    test_case.assertEqual(list(step1.required_certifications.all()), [])
    test_case.assertEqual(list(step1.creation_depends_on.all()), [])
    test_case.assertEqual(list(step1.submission_depends_on.all()), [])

    step2 = test_case.assertModelInstanceExists(
        Step,
        {
            'workflow_version': version2,
            'slug': 's2',
        },
        {
            'name': 'Step 2',
            'description': 'The second step',
            'is_human': True,
            'execution_function': {},
            'review_policy': {
                'policy': 'no_review',
            },
            'user_interface': {
                'angular_module': 'test_dir.v2.s2',
                'angular_directive': 's2',
                'javascript_includes': [
                    'test_dir/v2/s2/js/modules.js',
                    'test_dir/v2/s2/js/controllers.js',
                    'test_dir/v2/s2/js/directives.js',
                ],
            },
        })
    test_case.assertEqual(list(step2.required_certifications.all()),
                          [Certification.objects.get(
                              slug='certification2',
                              workflow__slug='test_dir',
                          )])
    test_case.assertEqual(list(step2.creation_depends_on.all()), [step1])
    test_case.assertEqual(list(step2.submission_depends_on.all()), [])
