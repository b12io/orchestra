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
    prerequisiteData: function(parentStep, desiredStep, dataKey) {
      var stepsToTraverse = [parentStep];
      while (stepsToTraverse.length) {
        var currentStep = stepsToTraverse.pop();
        if (currentStep.prerequisites.hasOwnProperty(desiredStep)) {
          var taskData = currentStep.prerequisites[desiredStep].task.data;
          if (taskData && dataKey) {
            return taskInfo[dataKey];
          }
          else {
            return taskData;
          }
        }
        for (var step in currentStep.prerequisites) {
          stepsToTraverse.push(currentStep.prerequisites[step]);
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
