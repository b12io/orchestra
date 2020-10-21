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

    getAssigmentsOrderedByList: function (orderedListOfSlugs, assignmentDataList) {
      return orderedListOfSlugs.reduce((acc, slug) => {
        const found = assignmentDataList.filter(a => a.stepSlug === slug)
        if (found.length > 0) {
          acc.push(found[0])
        }
        return acc
      }, [])
    }
  }
}
