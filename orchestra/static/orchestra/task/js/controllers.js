(function() {
  'use strict';

  angular
    .module('orchestra.task.controllers')
    .controller('TaskController', TaskController);

  function TaskController($location, $scope, $routeParams, $http, $rootScope,
    $modal, $timeout, autoSaveTask, orchestraService,
    requiredFields) {
    var vm = this;
    vm.taskId = $routeParams.taskId;
    vm.taskAssignment = {};
    vm.angularDirective = '';

    vm.activate = function() {
      $http.post('/orchestra/api/interface/task_assignment_information/', {
        'task_id': vm.taskId
      }).
      success(function(data, status, headers, config) {
        vm.taskAssignment = data;
        vm.project = data.project;
        vm.is_read_only = data.is_read_only;
        vm.work_times_seconds = data.work_times_seconds;

        if (!vm.is_read_only) {
          requiredFields.setup(vm);
          $scope.$watch('vm.taskAssignment.task.data', function(newVal, oldVal) {
            // Ensure save fired at initialization
            // [http://stackoverflow.com/a/18915585]
            if (newVal != oldVal) {
              $rootScope.$broadcast('task.data:change');
            }
          }, true);

          vm.autoSaver = autoSaveTask;
          autoSaveTask.setup($scope, vm.taskId, vm.taskAssignment.task.data);
        }

        var directiveTag = (window.orchestra
          .angular_directives[data.workflow.slug][data.workflow_version.slug]
          [data.step.slug]);

        var inject;
        if (directiveTag) {
          // Hyphenate and lowercase camel-cased directive names according to
          // angular standards.
          directiveTag = directiveTag.replace(/[A-Z]/g, function(letter, pos) {
            return (pos ? '-' : '') + letter.toLowerCase();
          });

          inject = [
            '<',
            directiveTag,
            ' task-assignment="vm.taskAssignment"></',
            directiveTag,
            '>'
          ].join('');
        }
        vm.angularDirective = inject;
      });
    };

    vm.confirmSubmission = function(command, totalSeconds) {
      vm.submitting = true;
      if (orchestraService.signals.fireSignal('submit.before') === false) {
        // If any of the registered signal handlers returns false, prevent
        // submit.
        vm.submitting = false;
        return;
      }
      $http.post('/orchestra/api/interface/submit_task_assignment/', {
          'task_id': vm.taskId,
          'task_data': vm.taskAssignment.task.data,
          'command_type': command,
          'work_time_seconds': totalSeconds
        })
        .success(function(data, status, headers, config) {
          // Prevent additional confirmation dialog on leaving the page; data
          // will be saved by submission
          vm.autoSaver.cancel();
          orchestraService.signals.fireSignal('submit.success');
          $location.path('/');
        })
        .error(function(data, status, headers, config) {
          orchestraService.signals.fireSignal('submit.error');
        })
        .finally(function() {
          orchestraService.signals.fireSignal('submit.finally');
          vm.submitting = false;
        });
    };

    vm.submitTask = function(command) {
      var modalInstance = $modal.open({
        templateUrl: 'submit_task_modal.html',
        controller: 'SubmitModalInstanceCtrl',
        size: 'sm',
        windowClass: 'modal-confirm-submit',
        resolve: {
          command: function() {
            return command;
          },
          work_times_seconds: function() {
            return vm.work_times_seconds;
          }
        },
      });

      modalInstance.result.then(function(totalSeconds) {
        vm.confirmSubmission(command, totalSeconds);
      });
    };

    vm.activate();
  }

})();


(function() {
  'use strict';

  angular
    .module('orchestra.task.controllers')
    .controller('SubmitModalInstanceCtrl', SubmitModalInstanceCtrl);

  SubmitModalInstanceCtrl.$inject = ['$scope', '$modalInstance', 'command', 'work_times_seconds'];

  function SubmitModalInstanceCtrl($scope, $modalInstance, command, workTimesSeconds) {
    $scope.command = command;
    $scope.currentIterationHours = null;
    $scope.currentIterationMinutes = null;
    $scope.workTimesSeconds = workTimesSeconds;

    $scope.submit = function() {
      $modalInstance.close($scope.totalSeconds());
    };

    $scope.cancel = function() {
      $modalInstance.dismiss('cancel');
    };

    $scope.totalSeconds = function() {
      var hours = parseInt($scope.currentIterationHours);
      var minutes = parseInt($scope.currentIterationMinutes);
      if (isNaN(hours)) {
        throw 'Please provide hours (0 is acceptable)';
      }
      if (hours.toString() !== $scope.currentIterationHours) {
        throw 'Hours should be a whole number';
      }
      if (hours < 0) {
        throw 'Hours should be >=0';
      }
      if (isNaN(minutes)) {
        throw 'Please provide minutes (0 is acceptable)';
      }
      if (minutes.toString() !== $scope.currentIterationMinutes) {
        throw 'Minutes should be a whole number';
      }
      if (minutes > 59 || minutes < 0) {
        throw 'Minutes should be <60 and >=0';
      }

      return (hours * 3600) + (minutes * 60);
    };

    $scope.secondsError = function() {
      try {
        $scope.totalSeconds();
      } catch (error) {
        return error;
      }

      return null;
    };

    $scope.hoursMinutes = function(seconds) {
      var hours = (seconds - (seconds % 3600)) / 3600;
      var minutes = (seconds % 3600) / 60;
      return [hours, minutes];
    };

    $scope.totalPreviousSeconds = function() {
      var total = 0;
      angular.forEach($scope.workTimesSeconds, function(seconds) {
        total += seconds;
      });
      return total;
    };

    $scope.totalPreviousHoursMinutes = function() {
      return $scope.hoursMinutes($scope.totalPreviousSeconds());
    };

    $scope.totalHoursMinutes = function() {
      var allSeconds = $scope.totalPreviousSeconds();
      try {
        allSeconds += $scope.totalSeconds();
      } catch (error) {}
      return $scope.hoursMinutes(allSeconds);
    };

    $scope.$watchGroup(['currentIterationHours',
        'currentIterationMinutes'
      ],
      function(newTimes, oldTimes) {
        for (var i = 0; i < newTimes.length; i++) {
          if (newTimes[i] != oldTimes[i]) {
            $scope.secondsErrorMessage = $scope.secondsError();
          }
        }
      });
  }
})();
