(function() {
  'use strict';

  angular
    .module('orchestra.dashboard.controllers')
    .controller('DashboardController', DashboardController);

  DashboardController.$inject = ['$scope', '$http', '$location', '$timeout',
                                'orchestraTasks'];

  function DashboardController($scope, $http, $location, $timeout,
                               orchestraTasks) {
    var vm = this;

    // Surface service to interpolator
    vm.orchestraTasks = orchestraTasks;

    vm.waiting = false;

    vm.newTask = function(taskType) {
      // To allow users to read the "no tasks left" message while debouncing
      // further clicks, we leave the message up for 15 seconds before removing
      // it and re-enabling the buttons
      if (!vm.noTaskTimer) {
        // Initialize task timer to dummy value to prevent subsequent API calls
        vm.noTaskTimer = 'temp';
        orchestraTasks.newTask(taskType)
          .then(function(response) {
            $location.path('task/' + data.id);
            vm.noTaskTimer = undefined;
          }, function(response) {
            vm.new_tasks = 0;
            // Rate limit button-clicking
            vm.noTaskTimer = $timeout(function() {
              vm.noTaskTimer = undefined;
              vm.new_tasks = undefined;
            }, 15000);
          });
      }
    };

    vm.waiting = true;
    orchestraTasks.updateTasks().finally(function() {
      vm.waiting = false;
    });
  }
})();
