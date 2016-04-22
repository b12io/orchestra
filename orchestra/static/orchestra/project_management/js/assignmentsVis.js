(function() {
  'use strict';

  var serviceModule = angular.module('orchestra.project_management');

  serviceModule.factory('assignmentsVis', function(dataService, orchestraApi, iterationsVis, visUtils) {
    /**
     * Service to modularize assignment visualization and manipulation within
     * the project management view.
     */
    var _vis;
    var assignmentsVis;

    return {
      addingAssignment: false,
      setup: function(vis) {
        _vis = vis;
        assignmentsVis = this;
      },
      draw: function() {
        /**
         * Draws/updates assignments within project management visualization.
         */
        var tasks = visUtils.parentContainer.selectAll('.task');

        var assignments = tasks.selectAll('.assignment')
          .data(function(taskKey) {
            var assignments = dataService.taskFromKey(taskKey).assignments.map(function(assignment) {
              return dataService.keyFromAssignment(assignment);
            });
            assignments.push();
            return assignments;
          });

        assignments.exit().remove();
        var assignmentsEnter = assignments.enter().append('g')
          .attr('class', 'assignment');

        iterationsVis.draw();

        assignmentsEnter.append('circle')
          .attr({
            'class': 'active-assignment',
            'cx': 0,
            'cy': 15,
            'r': 5,
          });

        assignments.selectAll('.active-assignment').attr({
          'fill': function(assignmentKey) {
            var assignment = dataService.assignmentFromKey(assignmentKey);
            return assignment.status == 'Submitted' ? 'rgb(0, 121, 191)' : 'white';
          },
          'stroke': function(assignmentKey) {
            var assignment = dataService.assignmentFromKey(assignmentKey);
            return assignment.status == 'Submitted' ? 'white' : 'rgb(0, 121, 191)';
          }
        });

        this.drawAssignmentTools();
      },
      drawAssignmentTools: function() {
        /**
         * Draws absolute-positined HTML elements to allow for assignment
         * manipulation.
         */
        var assignmentsVis = this;
        var assignmentsMeta = visUtils.parentContainer
          .selectAll('.task-view')
          .selectAll('.assignment-meta')
          .data(function(taskKey) {
            return dataService.taskFromKey(taskKey).assignments
              .map(function(assignment) {
                return dataService.keyFromAssignment(assignment);
              });
          });

        assignmentsMeta.exit().remove();
        var assignmentsMetaEnter = assignmentsMeta.enter()
          .append('div')
          .attr('class', 'assignment-meta');

        assignmentsMetaEnter.append('input')
          .attr({
            'class': 'worker-name readonly',
          })
          .on('click', function() {
            d3.select(this).classed('readonly', false);
          })
          .on('blur', function(assignmentKey) {
            var assignment = dataService.assignmentFromKey(assignmentKey);
            this.value = assignment.task.is_human ? assignment.worker.username : 'Machine';
            d3.select(this).classed('readonly', true);
          });

        assignmentsMeta.selectAll('.worker-name')
          .attr({
            'placeholder': function(assignmentKey) {
              var assignment = dataService.assignmentFromKey(assignmentKey);
              return assignment.worker.username || !assignment.task.is_human ? '' : 'Add new assignment';
            }
          })
          .on('keydown', function(assignmentKey) {
            var assignment = dataService.assignmentFromKey(assignmentKey);
            if (d3.event.keyCode == 13 && assignment.task.is_human) {
              if (!assignment.worker.username) {
                assignmentsVis.assign_task(assignment.task, d3.select(this));
              } else {
                assignmentsVis.reassignAssignment(assignment, d3.select(this));
              }
            }
          })
          .each(function(assignmentKey) {
            var assignment = dataService.assignmentFromKey(assignmentKey);
            this.value = assignment.task.is_human ? assignment.worker.username : 'Machine';
          });
      },
      assign_task: function(task, inputEl) {
        /**
         * Handles the promise returned by orchestraApi.assignTask in the
         * visualization.
         */
        var assignmentsVis = this;
        if (assignmentsVis.addingAssignment) {
          return;
        }
        assignmentsVis.addingAssignment = true;
        orchestraApi.assignTask(task, inputEl.node().value)
          .then(function() {
            inputEl.node().blur();
            dataService.updateData();
          }, function(response) {
            inputEl.node().value = '';
            inputEl.node().blur();
            var errorMessage = 'Error assigning task.';
            if (response.status === 400) {
              errorMessage = response.data.message;
            }
            alert(errorMessage);
          })
          .finally(function() {
            assignmentsVis.addingAssignment = false;
          });
      },
      reassignAssignment: function(assignment, inputEl) {
        /**
         * Handles the promise returned by orchestraApi.reassignAssignment in
         * the visualization.
         */
        if (assignment.reassigning) {
          return;
        }
        assignment.reassigning = true;
        orchestraApi.reassignAssignment(assignment, inputEl.node().value)
          .then(function() {
            assignment.worker.username = inputEl.node().value;
            assignmentsVis.draw();
          }, function(response) {
            inputEl.node().blur();
            var errorMessage = 'Error reassigning worker.';
            if (response.status === 400) {
              errorMessage = response.data.message;
            }
            alert(errorMessage);
          })
          .finally(function() {
            inputEl.node().blur();
            inputEl.node().value = assignment.worker.username;
            assignment.reassigning = false;
          });
      },
    };
  });
})();
