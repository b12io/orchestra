(function() {
  'use strict';

  var serviceModule = angular.module('orchestra.common');
  serviceModule.factory('orchestraService', function() {
    var googleUtils = {
      folders: {
        externalUrl: function(id) {
          return 'https://drive.google.com/open?id=' + id;
        },
        embedUrl: function(id) {
          return 'https://drive.google.com/embeddedfolderview?id=' + id;
        },
        embedListUrl: function(id) {
          return this.embedUrl(id) + '#list';
        },
        embedGridUrl: function(id) {
          return this.embedUrl(id) + '#grid';
        },
      },
      files: {
        editUrl: function(id) {
          return 'https://docs.google.com/document/d/' + id + '/edit';
        },
      },
    };
    var taskUtils = {
      prerequisiteData: function(taskAssignment, desiredStep, dataKey) {
        var previousData = taskAssignment.prerequisites[desiredStep];
        if (dataKey && previousData) {
          return previousData[dataKey];
        }
        return previousData;
      },
      updateVersion: function(taskAssignment) {
        if (taskAssignment === undefined ||
          taskAssignment.task.data.__version <= 1) {
          taskAssignment.task.data = {
            __version: 1
          };
        }
      },
    };
    var registered = {};
    var signals = {
      registerSignal: function(signalType, callback) {
        registered[signalType] = registered[signalType] || [];
        registered[signalType].push(callback);
      },
      fireSignal: function(signalType) {
        var success = true;
        registered[signalType] = registered[signalType] || [];
        registered[signalType].forEach(function(callback) {
          success = callback() && success;
        });
        return success;
      },
    };

    var orchestraService = {
      googleUtils: googleUtils,
      taskUtils: taskUtils,
      signals: signals,
    };
    return orchestraService;
  });

  serviceModule.factory('orchestraTasks', function($http) {
    var orchestraTasks = {
      data: null,
      tasks: {
        'pending': [],
        'returned': [],
        'in_progress': [],
        'completed': []
      },
      tasksByAssignmentId: {},
      preventNew: false,
      reviewerStatus: false,
      currentTask: undefined,
      updateTasks: function() {
        var service = this;

        service.data = $http.get('/orchestra/api/interface/dashboard_tasks/')
          .then(function(response) {
            service.tasks = response.data.tasks;

            service.allTasks().forEach(function(task) {
              service.tasksByAssignmentId[task.assignment_id] = task;
            });

            service.preventNew = response.data.preventNew;
            service.reviewerStatus = response.data.reviewerStatus;
          });
      },
      newTask: function(taskType) {
        var service = this;

        return $http.get('/orchestra/api/interface/new_task_assignment/' + taskType + '/')
          .then(function(response) {
            var task = response.data;
            service.tasks.in_progress.push(task);
            service.tasksByAssignmentId[task.assignment_id] = task;
          });
      },
      allTasks: function() {
        var tasks = [];
        for (var type in this.tasks) {
          tasks = tasks.concat(this.tasks[type]);
        }
        return tasks;
      },
      tasksForType: function(taskType) {
        return this.tasks[taskType];
      },
      numActiveTasks: function() {
        var numTasks = 0;
        for (var taskType in this.tasks) {
          if (taskType != 'complete') {
            numTasks += this.tasksForType(taskType).length;
          }
        }
        return numTasks;
      },
      getDescription: function(task) {
        if (task) {
          return task.detail + ' (' + task.step + ')';
        }
      }
    };

    orchestraTasks.updateTasks();
    return orchestraTasks;
  });
})();
