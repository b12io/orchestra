var serviceModule = angular.module('orchestra.common.services');

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
    findPrerequisite: function(parent_step, desired_slug) {
      var stepsToTraverse = [parent_step];
      while (stepsToTraverse.length) {
        var currentStep = stepsToTraverse.pop();
        if (currentStep.prerequisites[desired_slug]) {
          return currentStep.prerequisites[desired_slug];
        }
        for (var step_slug in currentStep.prerequisites) {
          stepsToTraverse.push(currentStep.prerequisites[step_slug]);
        }
      }
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
    'googleUtils': googleUtils,
    'taskUtils': taskUtils,
    'signals': signals,
  };
  return orchestraService;
});

serviceModule.factory('orchestraTasks', function($http) {
  return {
    tasks: {
      'pending': [],
      'returned': [],
      'in_progress': [],
      'completed': []
    },
    preventNew: false,
    reviewerStatus: false,
    newTask: function(taskType) {
      var service = this;

      return $http.get('/orchestra/api/interface/new_task_assignment/' + taskType + '/')
        .then(function(response) {
          service.tasks.in_progress.push(response.data);
        });
    },
    updateTasks: function() {
      var service = this;

      return $http.get('/orchestra/api/interface/dashboard_tasks/')
        .then(function(response) {
          service.tasks = response.data.tasks;
          service.preventNew = response.data.preventNew;
          service.reviewerStatus = response.data.reviewerStatus;
        });
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
    }
  };
});
