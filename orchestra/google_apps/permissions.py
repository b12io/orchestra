# Read permission for any user with the link.
read_with_link_permission = {'withLink': False,
                             'value': 'any',
                             'kind': 'drive#permission',
                             'name': 'Read with link permission',
                             'type': 'anyone',
                             'role': 'reader'}

# Write permission for any user with the link.
write_with_link_permission = {'kind': 'drive#permission',
                              'type': 'anyone',
                              'role': 'writer',
                              'withLink': True}
