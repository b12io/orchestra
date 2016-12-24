let d3 = require('d3')

export default function visUtils (dataService) {
  /**
   * Service to provide common visualization helpers across project
   * management components.
   */
  return {
    setup: function (parentContainer, params) {
      this.parentContainer = parentContainer
      this.params = params
    },
    svgLeftMargin: function () {
        /**
         * Calculates width of the frozen pane containing task step slugs and
         * other data.
         */
      return d3.select('.freeze-pane-left').node().getBoundingClientRect().width
    },
    getTaskHeight: function (task) {
        /**
         * Calculates the height of an individual task visualization.
         */
      var numAssignments = 1
      var taskKey = dataService.keyFromTask(task)
      if (dataService.taskMeta(taskKey, 'expandAssignments')) {
        numAssignments = task.assignments.length + 1
      }
      return (this.params.barHeight * numAssignments +
          this.params.lanePadding.top +
          this.params.lanePadding.bottom)
    },
    getSvgHeight: function () {
        /**
         * Totals the heights of all the project's task visualizations.
         */
      var utils = this
      var svgHeight = this.params.scaleHeight
      for (var stepSlug in dataService.data.tasks) {
        var task = dataService.data.tasks[stepSlug]
        svgHeight += utils.getTaskHeight(task)
      }
      return svgHeight
    },
    getSvgWidth: function () {
        /**
         * Calculates the desired width of the view.
         */
      return this.params.scaleWidth + this.params.marginRight
    },
    translateString: function (x, y) {
        /**
         * Returns a translate string for the given coordinates.
         */
      return 'translate(' + x + ', ' + y + ')'
    }
  }
}
