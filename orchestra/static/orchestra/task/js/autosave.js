(function() {
  'use strict';

  var serviceModule =  angular.module('orchestra.task.services');

  serviceModule.factory('autoSaveTask', function($rootScope, $timeout, $http, orchestraService) {
    var autoSaveTask = new function() {
      var autoSaver = this;

      autoSaver.setup = function($scope, taskId, taskData) {
        autoSaver.saveError = false;
        autoSaver.saving = false;
        autoSaver.timeout = 10000;
        autoSaver.taskId = taskId;
        autoSaver.data = taskData;
        autoSaver.scope = $scope;

        var handler = $rootScope.$on('task.data:change', function() {
          autoSaver.schedule();
        });
        $scope.$on('$destroy', handler);

        // Browser close or reload
        window.onbeforeunload = function() {
          if (autoSaver.autoSaveTimer || autoSaver.saveError) {
            return 'Your latest changes haven\'t been saved.'
          }
        }

        // Angular location change
        $scope.$on('$locationChangeStart', function(e) {
          if (autoSaver.autoSaveTimer || autoSaver.saveError) {
            if (!confirm('Your latest changes haven\'t been saved.\n\n' +
                  'Are you sure you want to leave this page?')) {
              // Disable confirm dialog if navigating away from task view.
              window.onbeforeunload = null;
              e.preventDefault();
            }
          }
        });
      }

      autoSaver.schedule = function() {
        if (!autoSaver.autoSaveTimer && !autoSaver.scope.is_read_only) {
          autoSaver.autoSaveTimer = $timeout(function() {
            autoSaver.save();
          }, autoSaver.timeout)
        }
      }

      autoSaver.cancel = function() {
        $timeout.cancel(autoSaver.autoSaveTimer);
        autoSaver.autoSaveTimer = undefined;
      }

      autoSaver.save = function() {
        if (autoSaver.scope.is_read_only) {
          return;
        }
        autoSaver.saving = true;
        autoSaver.saveError = false;
        autoSaver.cancel();
        orchestraService.signals.fireSignal('save.before');
        $http.post('/orchestra/api/interface/save_task_assignment/',
             {'task_id': autoSaver.taskId, 'task_data': autoSaver.data})
        .success(function(data, status, headers, config) {
          autoSaver.lastSaved = Date.now();
          // Reset timeout counter on save success
          autoSaver.timeout = 10000;
          orchestraService.signals.fireSignal('save.success');
        })
        .error(function(data, status, headers, config) {
          autoSaver.saveError = true;
          orchestraService.signals.fireSignal('save.error');
        })
        .finally(function() {
          orchestraService.signals.fireSignal('save.finally');
          autoSaver.saving = false;
          if (autoSaver.saveError) {
            // Retry save with exp backoff
            autoSaver.timeout *= 2;
            autoSaver.schedule();
          }
        });
      };
    }

    return autoSaveTask;
  });
})()
