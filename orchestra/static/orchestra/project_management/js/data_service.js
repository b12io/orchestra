(function() {
  'use strict';

  var serviceModule = angular.module('orchestra.project_management');

  serviceModule.factory('dataService', function($rootScope, $location, orchestraApi) {
    /**
     * Service to share and manipulate project management data across
     * visualization components.
     */
    var _meta;
    var _now = new Date();

    return {
      setup: function(projectId) {
        _meta = {
          'tasks': {}
        };
        this.projectId = projectId;
      },
      updateData: function(cb) {
        /**
         * Retrieves latest project data from Orchestra.
         */
        var dataService = this;
        orchestraApi.projectInformation(this.projectId)
          .then(function(response) {
            dataService.setData(response.data);
            if (dataService.data.project.status === 'Aborted') {
              alert('Project is aborted.');
              $location.path('/');
            } else {
              $rootScope.$broadcast('orchestra:projectManagement:dataUpdate');
              if (cb) {
                cb();
              }
            }
          }, function(response) {
            var errorMessage = 'Error updating data.';
            if (response.status === 400) {
              errorMessage = response.data.message;
            }
            alert(errorMessage);
          });
      },
      setData: function(data) {
        /**
         * Prepares raw project data for visualization.
         */
        this.data = data;

        var steps = {};
        this.data.steps.forEach(function(step) {
          steps[step.slug] = step;
        });

        this.data.steps = steps;

         /*jshint -W083 */
        // Hide error for creating a function in a loop
        for (var step_slug in this.data.tasks) {
          var task = this.data.tasks[step_slug];
          task.is_human = this.data.steps[task.step_slug].is_human;
          if (this.awaitingAssignment(task)) {
            // TODO(jrbotros): create the empty assignment in a saner way
            task.assignments.push({
              iterations: [],
              start_datetime: task.start_datetime,
              status: 'Processing',
              worker: {id: null, username: null},
            });
          }
          task.assignments.forEach(function(assignment) {
            assignment.task = task;
            assignment.iterations.forEach(function(iteration, i) {
              iteration.assignment = assignment;
            });
          });
        }

        var dataService = this;
        this.timeSortedSlugs = Object.keys(this.data.tasks).sort(function(a, b) {
          var previousTask = dataService.data.tasks[a];
          var nextTask = dataService.data.tasks[b];
          return d3.ascending(new Date(previousTask.start_datetime),
            new Date(nextTask.start_datetime));
        });
      },
      taskFromKey: function(key) {
        /**
         * Returns the task for a given key.
         */
        return this.data.tasks[key];
      },
      keyFromTask: function(task) {
        /**
         * Returns the key for a given task.
         */
        return task.step_slug;
      },
      awaitingAssignment: function(task) {
        /**
         * Determines whether task can be given a new assignment.
         */
        var statuses = ['Awaiting Processing', 'Pending Review'];
        return statuses.indexOf(task.status) >= 0;
      },
      inProgressAssignment: function(task) {
        /**
         * Determines whether task has a currently-processing assignment.
         */
        var statuses = ['Processing', 'Post-review Processing', 'Reviewing'];
        return statuses.indexOf(task.status) >= 0 || this.awaitingAssignment(task);
      },
      taskMeta: function(taskKey, metaKey, value) {
        /**
         * Stores and reads keyed task metadata. Since we update data from the
         * server, we store task visualization data separately so it's not
         * overwritten.
         */
        var taskMeta = _meta.tasks[taskKey] || {};
        if (value !== undefined) {
          taskMeta[metaKey] = value;
          _meta.tasks[taskKey] = taskMeta;
        } else {
          return taskMeta[metaKey];
        }
      },
      taskEnd: function(task) {
        /**
         * Calculates the end time for a given task.
         */
        if (this.awaitingAssignment(task)) {
          return _now.toString();
        }
        var taskEnd = task.start_datetime;
        task.assignments.forEach(function(assignment) {
          if (assignment.iterations.length) {
            var lastIteration = assignment.iterations[assignment.iterations.length - 1];
            if (new Date(lastIteration.end_datetime) > new Date(taskEnd)) {
              taskEnd = lastIteration.end_datetime;
            }
          }
        });
        return taskEnd;
      },

      assignmentFromKey: function(key) {
        /**
         * Returns the assignment for a given key.
         */
        return this.taskFromKey(key.taskKey)
          .assignments[key.assignmentIndex];
      },
      keyFromAssignment: function(assignment) {
        /**
         * Returns the key for a given assignment.
         */
        var dataService = this;
        return {
          'taskKey': dataService.keyFromTask(assignment.task),
          'assignmentIndex': dataService.indexFromAssignment(assignment)
        };
      },
      indexFromAssignment: function(assignment) {
        /**
         * Returns the assignment counter for a given assignment.
         */
        return assignment.task.assignments.indexOf(assignment);
      },

      iterationFromKey: function(key) {
        /**
         * Returns the iteration for the given key.
         */
        return this.assignmentFromKey(key.assignmentKey).iterations[key.iterationIndex];
      },
      keyFromIteration: function(iteration) {
        /**
         * Returns the key for a given iteration.
         */
        var dataService = this;
        return {
          'assignmentKey': dataService.keyFromAssignment(iteration.assignment),
          'iterationIndex': iteration.assignment.iterations.indexOf(iteration)
        };
      }
    };
  });
})();
