from copy import deepcopy
from dateutil.parser import parse
from dateutil.tz import tzutc

from orchestra.core.errors import SnapshotsError


VERSION = '__version'
SNAPSHOTS = 'snapshots'
DATETIME = 'datetime'
TIME_WORKED = 'work_time_seconds'


def empty_snapshots():
    return {SNAPSHOTS: [],
            VERSION: 2}


def load_snapshots(snapshots):
    """
    Given a task assignment `snapshots` object, ensures that it follows
    the latest snapshots schema.
    """
    snapshots = deepcopy(snapshots)
    version = snapshots.get(VERSION)
    if version is None:
        snapshot_list = snapshots.get(SNAPSHOTS, [])
        for snapshot_data in snapshot_list:
            snapshot_data[TIME_WORKED] = snapshot_data.get(TIME_WORKED, 0)
        snapshots[SNAPSHOTS] = snapshot_list
        snapshots[VERSION] = 1
    if snapshots[VERSION] == 1:
        snapshot_list = snapshots.get(SNAPSHOTS, [])
        for snapshot_data in snapshot_list:
            snapshot_data[DATETIME] = parse(
                snapshot_data[DATETIME]).replace(tzinfo=tzutc()).isoformat()
        snapshots[SNAPSHOTS] = snapshot_list
        snapshots[VERSION] = 2
    if snapshots[VERSION] != 2:
        raise SnapshotsError('Task Assignment snapshots were an '
                             'unrecognized version: {}'.format(snapshots))
    return snapshots
