import json
import os

from orchestra.core.errors import WorkflowError


def parse_workflow_directory(workflow_directory):
    parsed = {
        'versions': [],
    }

    # Verify that the directory exists.
    if not os.path.exists(workflow_directory):
        raise WorkflowError('Workflow directory does not exist.')

    # Look for and parse the workflow manifest.
    workflow_files = os.listdir(workflow_directory)
    if 'workflow.json' not in workflow_files:
        raise WorkflowError('No "workflow.json" manifest file found.')
    with open(os.path.join(workflow_directory, 'workflow.json'), 'r') as f:
        parsed['workflow'] = json.load(f)

    # Look for and parse workflow version subdirectories.
    workflow_subdirs = [
        os.path.join(workflow_directory, workflow_file)
        for workflow_file in workflow_files
        if os.path.isdir(os.path.join(workflow_directory, workflow_file))]
    for version_directory in workflow_subdirs:
        version_files = os.listdir(version_directory)
        if 'version.json' not in version_files:
            continue  # Subdirectory wasn't a workflow version.

        with open(os.path.join(version_directory, 'version.json'), 'r') as f:
            parsed['versions'].append(json.load(f))

    # Complain if the workflow has no versions.
    if len(parsed['versions']) == 0:
        raise WorkflowError('Workflow directory {} does not contain any '
                            'versions'.format(workflow_directory))
    return parsed
