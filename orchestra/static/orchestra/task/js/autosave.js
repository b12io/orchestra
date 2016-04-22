(function() {
  'use strict';

  var serviceModule = angular.module('orchestra.task');

  serviceModule.factory('autoSaveTask', function($rootScope, $timeout, $http, orchestraService) {
    return {
      setup: function($scope, taskId, taskData) {
        var service = this;
        service.saveError = false;
        service.saving = false;
        service.timeout = 10000;
        service.taskId = taskId;
        service.data = taskData;
        service.scope = $scope;

        var handler = $rootScope.$on('task.data:change', function() {
          service.schedule();
        });
        $scope.$on('$destroy', handler);

        // Browser close or reload
        window.onbeforeunload = function() {
          if (service.autoSaveTimer || service.saveError) {
            return 'Your latest changes haven\'t been saved.';
          }
        };

        // Angular location change
        $scope.$on('$locationChangeStart', function(e) {
          if (service.autoSaveTimer || service.saveError) {
            if (!confirm('Your latest changes haven\'t been saved.\n\n' +
              'Are you sure you want to leave this page?')) {
              // Disable confirm dialog if navigating away from task view.
              window.onbeforeunload = null;
              e.preventDefault();
            }
          }
        });
      },
      schedule: function() {
        var service = this;
        if (!service.autoSaveTimer && !service.scope.is_read_only) {
          service.autoSaveTimer = $timeout(function() {
            service.save();
          }, service.timeout);
        }
      },
      cancel: function() {
        var service = this;
        $timeout.cancel(service.autoSaveTimer);
        service.autoSaveTimer = undefined;
      },
      save: function() {
        var service = this;
        if (service.scope.is_read_only) {
          return;
        }
        service.saving = true;
        service.saveError = false;
        service.cancel();
        if (orchestraService.signals.fireSignal('save.before') === false) {
          // If any of the registered signal handlers returns false, prevent
          // save.
          service.saving = false;
          return;
        }
        $http.post('/orchestra/api/interface/save_task_assignment/', {
            'task_id': service.taskId,
            'task_data': service.data
          })
          .success(function(data, status, headers, config) {
            service.lastSaved = Date.now();
            // Reset timeout counter on save success
            service.timeout = 10000;
            orchestraService.signals.fireSignal('save.success');
          })
          .error(function(data, status, headers, config) {
            service.saveError = true;
            orchestraService.signals.fireSignal('save.error');
          })
          .finally(function() {
            orchestraService.signals.fireSignal('save.finally');
            service.saving = false;
            if (service.saveError) {
              // Retry save with exp backoff
              service.timeout *= 2;
              service.schedule();
            }
          });
      },
    };
  });
})();
