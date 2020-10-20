export default function helpers () {
  return {
    isTaskStaffable: function (taskStatus) {
      return taskStatus !== 'Complete' && taskStatus !== 'Aborted'
    }
  }
}
