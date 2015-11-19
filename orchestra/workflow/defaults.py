def get_default_assignment_policy(is_human):
    """ Return the default assignment policy.

    Args:
        is_human (bool):
            Indicates whether the policy is for a human or machine.

    Returns:
        default_policy (dict):
            A dictionary specifying the assignment policy.
    """
    return {} if not is_human else {
        'policy': 'anyone_certified'
    }


def get_default_review_policy(is_human):
    """ Return the default review policy.

    Args:
        is_human (bool):
            Indicates whether the policy is for a human or machine.

    Returns:
        default_policy (dict):
            A dictionary specifying the assignment policy.
    """
    return {} if not is_human else {
        'policy': 'sampled_review',
        'rate': 1,
        'max_reviews': 1
    }
