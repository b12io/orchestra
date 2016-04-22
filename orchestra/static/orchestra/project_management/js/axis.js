(function() {
  'use strict';

  var serviceModule = angular.module('orchestra.project_management');

  serviceModule.factory('axis', function(dataService, visUtils) {
    /**
     * Service to handle aligning visualization elements to a common time axis.
     */
    return {
      draw: function() {
        /**
         * Draws/updates axis with both relative and local time scales.
         */
        visUtils.parentContainer.select('.x.axis').style('opacity', 0);
        if (!dataService.timeSortedSlugs.length) {
          return;
        }
        var firstTask = dataService.data.tasks[dataService.timeSortedSlugs[0]];
        var minDatetime = new Date(firstTask.start_datetime);
        var taskEndTimes = dataService.timeSortedSlugs.map(function(slug) {
          return dataService.taskEnd(dataService.taskFromKey(slug));
        });

        var maxDatetime = minDatetime;
        taskEndTimes.forEach(function(datetime_string) {
          var nextDatetime = new Date(datetime_string);
          if (nextDatetime > minDatetime) {
            maxDatetime = nextDatetime;
          }
        });

        var hourInMilliseconds = 60 * 60 * 1000;
        var numHours = Math.ceil((maxDatetime - minDatetime) / hourInMilliseconds);
        maxDatetime = new Date(minDatetime.getTime() + numHours * hourInMilliseconds);

        var hourTicks = d3.range(0, numHours + 1).map(function(hourIndex) {
          return new Date(minDatetime.getTime() + hourIndex * hourInMilliseconds);
        });

        this.timeScale = d3.time.scale()
          .domain([minDatetime, maxDatetime])
          .range([0, visUtils.params.scaleWidth]);

        var xAxis = d3.svg.axis()
          .scale(this.timeScale)
          .tickSize(10);

        var tickSpread = 5;
        var xLabelText;
        if (this.relativeTime) {
          xAxis.tickValues(hourTicks)
            .tickFormat(function(d, i) {
              if (hourTicks.length < tickSpread || i % tickSpread === 0) {
                return (d - minDatetime) / hourInMilliseconds;
              }
            });
          xLabelText = 'Time (hours)';
        } else {
          xAxis.ticks(d3.time.hour, 1);
          var defaultFormat = this.timeScale.tickFormat();
          xAxis.tickFormat(function(d, i) {
            return i % tickSpread === 0 ? defaultFormat(d) : '';
          });
          xLabelText = 'Time (local)';
        }

        visUtils.parentContainer.select('.x.label')
          .text(xLabelText)
          .style('right', visUtils.getSvgWidth() + 5 + 'px');

        visUtils.parentContainer.select('.x.axis').transition().call(xAxis);
        visUtils.parentContainer.select('.x.axis')
          .style('opacity', 1)
          .attr('width', visUtils.getSvgWidth());
      },
      getOffset: function(datetime) {
        /**
         * Calculates the axis offset for a given datetime string.
         */
        return this.timeScale(new Date(datetime));
      }
    };
  });
})();
