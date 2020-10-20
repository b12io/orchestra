export default function helpers () {
  return {
    isTaskStaffable: function (status) {
      return status !== 'Complete' && status !== 'Aborted'
    }
  }
}
