(function() {
  'use strict';

  angular
    .module('orchestra.task')
    .controller('TaskController', TaskController);

  function TaskController($location, $scope, $routeParams, $http, $rootScope,
    $uibModal, $timeout, autoSaveTask, orchestraService, orchestraTasks,
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

        orchestraTasks.data.then(function() {
          orchestraTasks.currentTask = orchestraTasks.tasksByAssignmentId[vm.taskAssignment.assignment_id];
          $scope.$on('$locationChangeStart', function() {
            orchestraTasks.currentTask = undefined;
          });
        });

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

    vm.confirmSubmission = function(command) {
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
        })
        .success(function(data, status, headers, config) {
          // Prevent additional confirmation dialog on leaving the page; data
          // will be saved by submission
          vm.autoSaver.cancel();
          orchestraService.signals.fireSignal('submit.success');
          orchestraTasks.updateTasks();
          $location.path('/timecard');
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
      if (confirm('Are you sure you want to submit this task?')) {
        vm.confirmSubmission(command);
      }
    };

    vm.activate();
  }
})();
