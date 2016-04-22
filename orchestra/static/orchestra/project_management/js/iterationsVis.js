(function() {
  'use strict';

  var serviceModule = angular.module('orchestra.project_management');

  serviceModule.factory('iterationsVis', function($uibModal, dataService, visUtils, axis) {
    /**
     * Service to modularize iteration visualization and manipulation within
     * the project management view.
     */
    return {
      relativeTime: true,
      draw: function() {
        /**
         * Draws/updates iterations within project management visualization.
         */
        var iterations = visUtils.parentContainer.selectAll('.task').selectAll('.assignment')
          .selectAll('.iteration')
          .data(function(assignmentKey) {
            var iterations = [];
            dataService.assignmentFromKey(assignmentKey).iterations.forEach(function(iteration, i) {
                iterations.push(dataService.keyFromIteration(iteration));
            });
            return iterations;
          });

        iterations.exit().remove();
        iterations.enter().append('rect')
          .attr({
            'class': 'iteration',
            'height': visUtils.params.barHeight,
            'stroke': 'none',
            'stroke-width': '2px',
            'fill': 'rgb(0, 121, 191)',
          })
          .on('mouseenter', function() {
            d3.select(this).attr('stroke', 'yellow');
          })
          .on('mouseleave', function() {
            d3.select(this).attr('stroke', 'none');
          })
          .on('click', function(iterationKey, i) {
            var iteration = dataService.iterationFromKey(iterationKey);
            var modalInstance = $uibModal.open({
              templateUrl: $static('/static/orchestra/project_management/partials/data_modal.html'),
              controller: function($scope) {
                $scope.data = Object.keys(iteration.submitted_data) ? iteration.submitted_data : iteration.assignment.in_progress_task_data;
                $scope.header = iteration.assignment.task.step_slug + ', ' +
                  iteration.assignment.worker.username + ', iteration ' + i;
                $scope.admin_url = iteration.assignment.admin_url;
              }
            });
          });

        iterations.transition().attr({
          'width': function(iterationKey) {
            var iteration = dataService.iterationFromKey(iterationKey);
            return axis.getOffset(iteration.end_datetime) - axis.getOffset(iteration.start_datetime);
          },
          'transform': function(iterationKey) {
            var iteration = dataService.iterationFromKey(iterationKey);
            return visUtils.translateString(
              (axis.getOffset(iteration.start_datetime) -
                axis.getOffset(iteration.assignment.task.start_datetime)), 0);
          },
          'opacity': function(iterationKey) {
            var iteration = dataService.iterationFromKey(iterationKey);
            var task = iteration.assignment.task;
            return (task.assignments.length - task.assignments.indexOf(iteration.assignment)) / task.assignments.length;
          }
        });
      }
    };
  });
})();
