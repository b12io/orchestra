import logging

from orchestra.google_apps.convenience import create_document_from_template
from orchestra.google_apps.convenience import create_folder_with_permissions
from orchestra.google_apps.permissions import write_with_link_permission

logger = logging.getLogger(__name__)


def create_documents(project_data, prerequisites):
    """Create documents and folders needed for the journalism workflow.

    The following will be created:
    * an 'Article Draft' document where a reporter can draft text.
    * a 'Raw Photos' folder where a photographer can upload images.

    Documents are created in the project root folder.
    """
    task_data = {}
    folder_id = project_data['project_folder_id']

    # Create an Article Draft document.
    article_draft_template = project_data['article_draft_template']
    task_data['articleURL'] = create_document_from_template(
        article_draft_template,
        'Article Draft',
        parent_ids=[folder_id],
        permissions=[write_with_link_permission],
    )['alternateLink']

    # Create a Raw Photos folder.
    task_data['raw_photo_folder'] = create_folder_with_permissions(
        folder_id,
        'Raw Photos',
        permissions=[write_with_link_permission],
    )['id']

    return task_data
