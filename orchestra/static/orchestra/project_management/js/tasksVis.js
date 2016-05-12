(function() {
  'use strict';

  var serviceModule = angular.module('orchestra.project_management');

  serviceModule.factory('tasksVis', function($uibModal, dataService, orchestraApi,
    visUtils, assignmentsVis, crosshair, axis) {
    /**
     * Service to modularize task visualization and manipulation within
     * the project management view.
     */
    var tasksVis;

    var _humanizeAudit = function(audit) {
      /**
       * Selectively render a revert audit in a human-readable way.
       */
      var humanAudit = {
        'step': audit.task.step_slug,
        'change': audit.change,
        'assignments': {},
      };
      audit.assignments.forEach(function(assignmentAudit) {
        humanAudit.assignments[assignmentAudit.assignment.worker.username] = {
          'change': assignmentAudit.change,
          'iterations': assignmentAudit.iterations
        };
      });
      return humanAudit;
    };

    var _hasOneClassFrom = function(target, classes) {
      /**
       * Determine if a d3 selection has at least one class from a given list.
       */
      var cls;
      for (var i = 0; i < classes.length; i++) {
        cls = target.classed(classes[i]);
        if (cls) {
          break;
        }
      }
      return cls;
    };


    return {
      reverting: false,
      draw: function() {
        /**
         * Draws/updates tasks within project management visualization.
         */
        var tasksVis = this;
        var taskViews = visUtils.parentContainer.selectAll('.task-view')
          .data(dataService.timeSortedSlugs, function(slug) {
            return slug;
          });
        taskViews.exit().remove();
        var taskViewsEnter = taskViews.enter().append('div')
          .attr('class', 'task-view');

        var taskSvgsEnter = taskViewsEnter.append('svg')
          .attr('class', 'task-svg')
          .style('margin-left', visUtils.params.marginLeft + 'px');

        taskViews.selectAll('.task-svg').attr('width', visUtils.getSvgWidth());
        taskViews.style('width', visUtils.getSvgWidth() + visUtils.params.marginLeft + 'px');

        var tasksEnter = taskSvgsEnter.append('g')
          .attr('class', 'task');

        taskViews.selectAll('.task')
          .transition()
          .attr({
            'transform': function(taskKey) {
              var task = dataService.taskFromKey(taskKey);
              return visUtils.translateString(axis.getOffset(task.start_datetime), visUtils.params.lanePadding.top);
            },
          });

        tasksVis.drawRevertFlags();

        assignmentsVis.draw();

        var taskRect = tasksEnter.append('rect')
          .attr({
            'class': 'task-rect',
            'height': visUtils.params.barHeight,
            'fill-opacity': 0,
            'stroke': 'black',
          });

        taskViews.selectAll('.task-rect')
          .transition()
          .attr('width', function(slug) {
            var task = dataService.taskFromKey(slug);
            return axis.getOffset(dataService.taskEnd(task)) - axis.getOffset(task.start_datetime);
          })
          .each(function(slug) {
            var task = dataService.taskFromKey(slug);
            tasksVis.expand(d3.select(tasksVis.parentNode));
          });

        taskViews.on('click', function(taskKey) {
          var task = dataService.taskFromKey(taskKey);
          var target = d3.select(d3.event.target);
          var classes = ['task-view', 'task-svg', 'task-rect'];
          if (!_hasOneClassFrom(target, classes)) {
            return;
          }
          task = dataService.taskFromKey(taskKey);
          var expandAssignments = dataService.taskMeta(taskKey, 'expandAssignments');
          dataService.taskMeta(taskKey, 'expandAssignments', !expandAssignments);
          tasksVis.distribute();
        });

        this.drawMeta();
        this.drawBackgrounds();
        tasksVis.distribute();
      },
      drawMeta: function() {
        /**
         * Draws task step slugs, statuses, and action buttons to the left of
         * the main project management visualization.
         */
        var tasksVis = this;
        var taskNames = d3.select('.task-names').selectAll('.task-name')
          .data(dataService.timeSortedSlugs, function(slug) {
            return slug;
          });
        taskNames.exit().remove();
        var taskNamesEnter = taskNames.enter().append('div')
          .attr('class', 'task-name');
        taskNamesEnter.append('span')
          .attr('class', 'step-slug');
        var taskActionWrappers = taskNamesEnter.append('div').attr('class', 'task-action-wrapper');
        var actions = taskNames.selectAll('.task-action-wrapper').selectAll('.skip-task')
          .data(function(taskKey) {
            return dataService.taskFromKey(taskKey).status != 'Complete' ? [taskKey] : [];
          });
        actions.exit().remove();
        actions.enter().append('button')
          .attr('class', 'skip-task task-action btn btn-danger btn-xs')
          .text('Skip task')
          .on('click', function(taskKey) {
            tasksVis.completeAndSkipTask(dataService.taskFromKey(taskKey));
          });
        taskActionWrappers.append('a')
          .attr({
            'href': function(taskKey) {
              return dataService.taskFromKey(taskKey).admin_url;
            },
            'target': '_blank',
            'class': 'task-action'
          })
          .append('button')
          .attr('class', 'btn btn-default btn-xs')
          .text('View in admin');

        taskNamesEnter.append('span').attr('class', 'step-status');

        taskNames.selectAll('.step-slug').text(function(slug) {
          var task = dataService.taskFromKey(slug);
          return task.step_slug + ' ' + task.id;
        });

        taskNames.selectAll('.step-status').text(function(slug) {
          var task = dataService.taskFromKey(slug);
          return task.status;
        });
      },
      drawBackgrounds: function() {
        /**
         * Renders each task "swim lane" with an alternating color.
         */
        d3.selectAll('.task-name')
          .style('background-color', function(slug, i, j) {
            return i % 2 === 0 ? '#eee' : 'white';
          });
        visUtils.parentContainer.selectAll('.task-view')
          .style('background-color', function(slug, i) {
            return i % 2 === 0 ? '#eee' : 'white';
          });
      },
      drawRevertFlags: function() {
        /**
         * Draws the flags corresponding to suitable task revert times.
         */
        var tasksVis = this;
        var tasks = visUtils.parentContainer.selectAll('.task');
        var revertGroups = tasks.selectAll('.revert-group').data(function(slug) {
          var task = dataService.taskFromKey(slug);
          var datetimes = [];
          task.assignments.forEach(function(assignment) {
            if (assignment.iterations) {
              assignment.iterations.forEach(function(iteration, i) {
                if (i === 0) {
                  // If iteration is the first of its assignment, we can
                  // revert to before it was created.
                  datetimes.push({
                    'datetime': new Date(iteration.start_datetime),
                    'taskKey': task.step_slug,
                    'iterationId': iteration.id,
                    'revertBefore': true
                  });
                }
                if (iteration.status !== 'Processing') {
                  // If iteration isn't processing, we can revert to it
                  datetimes.push({
                    'datetime': new Date(iteration.end_datetime),
                    'taskKey': task.step_slug,
                    'iterationId': iteration.id,
                    'revertBefore': false
                  });
                }
              });
            }
          });
          return datetimes;
        }, function(datetime) {
          return datetime.datetime;
        });
        revertGroups.exit().remove();
        var revertGroupsEnter = revertGroups.enter().append('g')
          .attr('class', 'revert-group');

        revertGroupsEnter.append('line')
          .attr({
            'class': 'revert-line',
            'stroke': 'rgb(0, 121, 191)',
          });

        // Revert flags
        revertGroupsEnter.append('path')
          .attr({
            'd': 'M0,0 V4 L-2,2 Z',
            'fill': 'rgb(0, 121, 191)',
            'transform': visUtils.translateString(0, -visUtils.params.lanePadding.top / 2) + ' scale(3, 3)',
          })
          .style('cursor', 'pointer')
          .on('mouseenter', function(datetimeInfo) {
            if (!tasksVis.reverting) {
              crosshair.move(datetimeInfo.datetime);
              crosshair.show();
            }
          })
          .on('mouseleave', function(datetimeInfo) {
            if (!tasksVis.reverting) {
              crosshair.hide();
            }
          })
          .on('click', function(datetimeInfo) {
            var taskId = dataService.taskFromKey(datetimeInfo.taskKey).id;
            tasksVis.revertTask(taskId, datetimeInfo.iterationId, datetimeInfo.revertBefore);
          });

        revertGroups.transition().attr({
          'transform': function(datetimeInfo) {
            var taskStartDatetime = dataService.taskFromKey(datetimeInfo.taskKey).start_datetime;
            return visUtils.translateString(
              axis.timeScale(datetimeInfo.datetime) - axis.getOffset(taskStartDatetime), 0
            );
          },
        });

        revertGroups.selectAll('.revert-line')
          .transition()
          .attr({
            'y1': -visUtils.params.lanePadding.top / 2,
            'y2': function(datetimeInfo) {
              var taskKey = datetimeInfo.taskKey;
              var task = dataService.taskFromKey(taskKey);
              if (dataService.taskMeta(taskKey, 'expandAssignments')) {
                return (task.assignments.length + 1) * visUtils.params.barHeight + 1;
              } else {
                return visUtils.params.barHeight + 1;
              }
            },
          });
      },
      expand: function() {
        /**
         * Toggles expansion of selected tasks to show more detailed assignment
         * data and actions.
         */
        var taskViews = d3.selectAll('.task-view');

        taskViews.selectAll('.assignments')
          .transition()
          .attr('transform', function(taskKey) {
            var expand = dataService.taskMeta(taskKey, 'expandAssignments');
            visUtils.translateString(0, expand ? visUtils.params.barHeight : 0);
          });

        taskViews.selectAll('.assignment')
          .transition()
          .attr({
            'transform': function(assignmentKey, i) {
              var assignment = dataService.assignmentFromKey(assignmentKey);
              var taskKey = dataService.keyFromTask(assignment.task);
              var expand = dataService.taskMeta(taskKey, 'expandAssignments');
              return visUtils.translateString(0, expand ? (visUtils.params.barHeight * (i + 1)) : 0);
            },
          });

        taskViews.selectAll('.assignment-meta')
          .transition()
          .style({
            'position': 'absolute',
            'top': function(assignmentKey, i) {
              var assignment = dataService.assignmentFromKey(assignmentKey);
              var taskKey = dataService.keyFromTask(assignment.task);
              var expand = dataService.taskMeta(taskKey, 'expandAssignments');
              if (expand) {
                return (visUtils.params.barHeight * (i + 1) + visUtils.params.lanePadding.top + 4) + 'px';
              }
              return visUtils.params.lanePadding.top + 'px';
            },
            'right': function(assignmentKey) {
              var assignment = dataService.assignmentFromKey(assignmentKey);
              return (visUtils.getSvgWidth() - axis.getOffset(assignment.task.start_datetime) + 10) + 'px';
            },
            'display': function(assignmentKey, i) {
              var assignment = dataService.assignmentFromKey(assignmentKey);
              var taskKey = dataService.keyFromTask(assignment.task);
              var expand = dataService.taskMeta(taskKey, 'expandAssignments');
              return expand ? 'inherit' : 'none';
            },
          });

        taskViews.selectAll('.active-assignment')
          .attr('display', function(assignmentKey) {
            var assignment = dataService.assignmentFromKey(assignmentKey);
            var taskKey = dataService.keyFromTask(assignment.task);
            var expand = dataService.taskMeta(taskKey, 'expandAssignments');
            return expand ? 'inherit' : 'none';
          });
      },
      distribute: function() {
        /**
         * Vertically distribute task visualizations inside their container.
         */
        visUtils.parentContainer.selectAll('.task-svg')
          .transition()
          .attr({
            'height': function(taskKey) {
              var task = dataService.taskFromKey(taskKey);
              return visUtils.getTaskHeight(task);
            },
          });

        var taskNamesWrapper = d3.selectAll('.task-names').style('margin-top', visUtils.params.scaleHeight + 'px');
        var taskNames = taskNamesWrapper.selectAll('.task-name')
          .transition()
          .style({
            'height': function(slug, i) {
              var task = dataService.taskFromKey(slug);
              return visUtils.getTaskHeight(task) + 'px';
            },
            'padding-top': visUtils.params.lanePadding.top / 2 + 'px'
          });

        this.drawRevertFlags();
        this.expand();
      },
      completeAndSkipTask: function(task) {
        /**
         * Handles the promise returned by orchestraApi.completeAndSkipTask
         * in the visualization.
         */
        if (!confirm('Are you sure you want to skip this task and mark it ' +
          'as complete? This might leave the project in a ' +
          'corrupted/unrecoverable state.')) {
          return;
        }
        orchestraApi.completeAndSkipTask(task)
          .then(function() {
            dataService.updateData();
          }, function(response) {
            var errorMessage = 'Error skipping task.';
            if (response.status === 400) {
              errorMessage = response.data.message;
            }
            alert(errorMessage);
          });
      },
      revertTask: function(taskId, iterationId, revertBefore) {
        /**
         * Displays a modal containing the audit trail of items to be reverted.
         * Handles the promise returned by orchestraApi.revertTask in the
         * visualization.
         */
        var tasksVis = this;
        if (tasksVis.reverting) {
          return;
        }
        tasksVis.reverting = true;
        orchestraApi.revertTask(taskId, iterationId, revertBefore, false)
          .then(function(response) {
            var modalInstance = $uibModal.open({
              templateUrl: $static('/static/orchestra/project_management/partials/revert_modal.html'),
              controller: function($scope) {
                $scope.audit = _humanizeAudit(response.data);
                $scope.cancel = modalInstance.close;
                $scope.confirmRevert = function() {
                  orchestraApi.revertTask(taskId, iterationId, revertBefore, true)
                    .then(function() {
                      dataService.updateData();
                    }, function(response) {
                      var errorMessage = 'Could not revert task.';
                      if (response.status === 400) {
                        errorMessage = response.data.message;
                      }
                      alert(errorMessage);
                    })
                    .finally(function() {
                      modalInstance.close();
                    });
                };
              }
            });

            modalInstance.result.finally(function() {
              tasksVis.reverting = false;
              crosshair.hide();
            });
          }, function(response) {
            var errorMessage = 'Could not generate revert information.';
            if (response.status === 400) {
              errorMessage = response.data.message;
            }
            alert(errorMessage);
          });
      },
    };
  });
})();
