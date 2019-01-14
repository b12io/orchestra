import moment from 'moment-timezone'

let d3 = require('d3')

export default function axis (dataService, visUtils) {
  /**
   * Service to handle aligning visualization elements to a common time axis.
   */
  'ngAnnotate'
  return {
    draw: function () {
      /**
       * Draws/updates axis with both relative and local time scales.
       */
      visUtils.parentContainer.select('.x.axis').style('opacity', 0)
      if (!dataService.timeSortedSlugs.length) {
        return
      }
      var projectId = dataService.currentProject.id
      var firstTask = dataService.data[projectId].tasks[dataService.timeSortedSlugs[0]]
      var minDatetime = new Date(firstTask.start_datetime)
      var taskEndTimes = dataService.timeSortedSlugs.map(function (slug) {
        return dataService.taskEnd(dataService.taskFromKey(slug))
      })

      var maxDatetime = minDatetime
      taskEndTimes.forEach(function (datetimeString) {
        var nextDatetime = new Date(datetimeString)
        if (nextDatetime > minDatetime) {
          maxDatetime = nextDatetime
        }
      })

      var hourInMilliseconds = 60 * 60 * 1000
      var numHours = Math.ceil((maxDatetime - minDatetime) / hourInMilliseconds)
      maxDatetime = new Date(minDatetime.getTime() + numHours * hourInMilliseconds)

      var hourStep = Math.ceil(numHours * 10 / visUtils.params.scaleWidth)

      var hourTicks = d3.range(0, numHours + 1, hourStep).map(function (hourIndex) {
        return new Date(minDatetime.getTime() + hourIndex * hourInMilliseconds)
      })

      this.timeScale = d3.time.scale()
        .domain([minDatetime, maxDatetime])
        .range([0, visUtils.params.scaleWidth])

      var tickSize = 6
      var xAxis = d3.svg.axis()
        .scale(this.timeScale)
        .tickSize(tickSize)
        .tickPadding(2 * tickSize)
        .tickValues(hourTicks)

      var tickSpread = 10
      var xLabelText
      if (this.relativeTime) {
        xAxis.tickFormat(function (d, i) {
          if (hourTicks.length < tickSpread || i % tickSpread === 0) {
            return (d - minDatetime) / hourInMilliseconds
          }
        })
        xLabelText = 'Time (hours)'
      } else {
        xAxis.tickFormat(function (d, i) {
          return i % tickSpread === 0 ? moment(d).format('M/DD ha') : ''
        })
        xLabelText = 'Time (local)'
      }

      visUtils.parentContainer.select('.x.label')
        .text(xLabelText)
        .style('right', visUtils.getSvgWidth() + 5 + 'px')

      visUtils.parentContainer.select('.x.axis').call(xAxis)
      visUtils.parentContainer.select('.x.axis')
        .style('opacity', 1)
        .attr('width', visUtils.getSvgWidth())

      visUtils.parentContainer.select('.x.axis')
        .selectAll('.tick line')
        .attr('y2', function (d, i) {
          return i % tickSpread === 0 ? 1.5 * tickSize : tickSize
        })
    },
    getOffset: function (datetime) {
      /**
       * Calculates the axis offset for a given datetime string.
       */
      return this.timeScale(new Date(datetime))
    }
  }
}
