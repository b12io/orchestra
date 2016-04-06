from orchestra.core.errors import TaskStatusError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TimeEntry
from orchestra.project_api.serializers import TimeEntrySerializer


def time_entries_for_worker(worker, task_id=None):
    """
    Gets time entries for a worker, and optionally for a specific task.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.
        task_id (int): optional
            The ID of the task to be associated with the time entry.

    Returns:
        serializer.data ([dict])
            list of serialized TimeEntry objects for given worker and
            optionally task.

    Raises:
        orchestra.models.Task.DoesNotExist:
            The specified task does not exist.
        orchestra.models.TaskAssignment.DoesNotExist
            The specified worker is not assigned to the specified task.
    """
    # TODO(lydia): add time constraint.
    time_entries = TimeEntry.objects.filter(assignment__worker=worker)
    if task_id:
        task = Task.objects.get(id=task_id)
        assignment = TaskAssignment.objects.get(worker=worker,
                                                task=task)
        time_entries = time_entries.filter(assignment=assignment)

    serializer = TimeEntrySerializer(time_entries, many=True)
    return serializer.data


def save_time_entry(worker, task_id, time_entry_data):
    """
    Saves time entry for task assignment.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.
        task_id (int):
            The ID of the task to be associated with the time entry.
        time_entry_data (dict):
            Dictionary of TimeEntry attributes

    Returns:
        time_entry (orchestra.models.TimeEntry)
            newly created time entry from time_entry_data

    Raises:
        orchestra.models.Task.DoesNotExist:
            The specified task does not exist.
        orchestra.core.errors.TaskStatusError:
            Saving time entry is not permitted for the given status.
        orchestra.models.TaskAssignment.DoesNotExist
            The specified worker is not assigned to the specified task.
        rest_framework.serializers.ValidationError
            The time entry data is invalid.
    """
    task = Task.objects.get(id=task_id)
    if task.status == Task.Status.COMPLETE:
        raise TaskStatusError('Task already completed')
    assignment = TaskAssignment.objects.get(worker=worker,
                                            task=task)
    time_entry_data['assignment'] = assignment.id
    serializer = TimeEntrySerializer(data=time_entry_data)
    if serializer.is_valid(raise_exception=True):
        time_entry = serializer.save()
        return time_entry
