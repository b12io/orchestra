from django.utils import timezone

from orchestra.core.errors import TaskStatusError
from orchestra.core.errors import TimerError
from orchestra.models import Task
from orchestra.models import TaskAssignment
from orchestra.models import TaskTimer
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


def _get_timer_object(worker, task_id):
    task = Task.objects.get(id=task_id)
    if task.status == Task.Status.COMPLETE:
        raise TaskStatusError('Task already completed')
    assignment = TaskAssignment.objects.get(worker=worker,
                                            task=task)
    try:
        timer = assignment.timer
    except TaskTimer.DoesNotExist:
        timer = TaskTimer.objects.create(worker=worker,
                                         assignment=assignment)
    return timer


def _reset_timer(timer):
    timer.start_time = None
    timer.stop_time = None
    timer.save()


def start_timer(worker, task_id):
    """
    Start timer for worker and task.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.
        task_id (int):
            The ID of the task to be associated with the time entry.

    Returns:
        timer (orchestra.models.TaskTimer)
            newly created timer object

    Raises:
        orchestra.models.Task.DoesNotExist:
            The specified task does not exist.
        orchestra.core.errors.TaskStatusError:
            Saving time entry is not permitted for the given status.
        orchestra.models.TaskAssignment.DoesNotExist
            The specified worker is not assigned to the specified task.
    """
    timer = _get_timer_object(worker, task_id)
    if timer.start_time is not None:
        raise TimerError('Timer has already started')
    timer.start_time = timezone.now()
    timer.save()
    return timer


def stop_timer(worker, task_id):
    """
    Stops timer for worker and task and creates a TimeEntry object.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.
        task_id (int):
            The ID of the task to be associated with the time entry.

    Returns:
        time_entry (orchestra.models.TimeEntry)
            newly created time entry from timer duration

    Raises:
        orchestra.models.Task.DoesNotExist:
            The specified task does not exist.
        orchestra.core.errors.TaskStatusError:
            Saving time entry is not permitted for the given status.
        orchestra.models.TaskAssignment.DoesNotExist
            The specified worker is not assigned to the specified task.
    """
    timer = _get_timer_object(worker, task_id)
    if timer.start_time is None:
        raise TimerError('Timer not started')
    timer.stop_time = timezone.now()
    timer.save()

    # Create TimeEntry object for timer.
    time_entry = TimeEntry.objects.create(
        date=timer.start_time.date(),
        time_worked=timer.stop_time - timer.start_time,
        assignment=timer.assignment,
        timer_start_time=timer.start_time,
        timer_stop_time=timer.stop_time)
    _reset_timer(timer)
    return time_entry


def get_timer_current_duration(worker, task_id):
    """
    Returns current time interval logged by timer.

    Args:
        worker (orchestra.models.Worker):
            The specified worker object.
        task_id (int):
            The ID of the task to be associated with the time entry.

    Returns:
        (datetime.timedelta)
            time interval since start of timer

    Raises:
        orchestra.models.Task.DoesNotExist:
            The specified task does not exist.
        orchestra.core.errors.TaskStatusError:
            Saving time entry is not permitted for the given status.
        orchestra.models.TaskAssignment.DoesNotExist
            The specified worker is not assigned to the specified task.
    """
    timer = _get_timer_object(worker, task_id)
    if timer.start_time is None:
        return None
    return timezone.now() - timer.start_time
