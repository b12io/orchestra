(function() {
  'use strict';

  angular
    .module('orchestra.dashboard.controllers')
    .controller('DashboardController', DashboardController);

  DashboardController.$inject = ['$scope', '$http', '$location', '$timeout'];

  function DashboardController($scope, $http, $location, $timeout) {
    var vm = this;

    vm.tasks = {
      'pending': [],
      'returned': [],
      'in_progress': [],
      'completed': []
    };
    vm.new_tasks = undefined;
    vm.numActiveTasks = function() {
      var numTasks = 0;
      for (var taskType in vm.tasks) {
        if (taskType != 'complete') {
          numTasks += vm.tasks[taskType].length;
        }
      }
      return numTasks;
    };
    vm.waiting = false;

    vm.activate = function() {
      vm.waiting = true;
      $http.get('/orchestra/api/interface/dashboard_tasks/').
      success(function(data, status, headers, config) {
        vm.tasks = data.tasks;
        vm.preventNewTasks = data.preventNewTasks;
        vm.reviewerStatus = data.reviewerStatus;
        vm.waiting = false;
      }).
      error(function(data, status, headers, config) {
        vm.waiting = false;
      });
    };

    vm.newTask = function(taskType) {
      // To allow users to read the "no tasks left" message while debouncing
      // further clicks, we leave the message up for 15 seconds before removing
      // it and re-enabling the buttons
      if (!vm.noTaskTimer) {
        // Initialize task timer to dummy value to prevent subsequent API calls
        vm.noTaskTimer = 'temp';
        $http.get('/orchestra/api/interface/new_task_assignment/' + taskType + '/').
        success(function(data, status, headers, config) {
          $location.path('task/' + data.id);
          vm.noTaskTimer = undefined;
        }).
        error(function(data, status, headers, config) {
          vm.new_tasks = 0;
          // Rate limit button-clicking
          vm.noTaskTimer = $timeout(function() {
            vm.noTaskTimer = undefined;
            vm.new_tasks = undefined;
          }, 15000);
        });
      }
    };

    vm.activate();
  }
})();
