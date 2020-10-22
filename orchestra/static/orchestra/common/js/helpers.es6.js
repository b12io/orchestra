const d3 = require('d3')

export default function helpers () {
  return {
    isTaskStaffable: function (taskStatus) {
      return taskStatus !== 'Complete' && taskStatus !== 'Aborted'
    },

    getSortedTasksSlugs: function (tasks) {
      return Object.keys(tasks).sort((a, b) => {
        const previousTask = tasks[a]
        const nextTask = tasks[b]
        return d3.ascending(
          new Date(previousTask.start_datetime),
          new Date(nextTask.start_datetime)
        )
      })
    },

    orderAssigmentsUsingListOfSlugs: function (orderedListOfSlugs, assignmentDataList) {
      assignmentDataList.sort((a, b) => {
        return orderedListOfSlugs.indexOf(a.stepSlug) - orderedListOfSlugs.indexOf(b.stepSlug)
      })
    }
  }
}
