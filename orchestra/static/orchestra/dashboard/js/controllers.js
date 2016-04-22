(function() {
  'use strict';

  angular
    .module('orchestra.dashboard')
    .controller('DashboardController', DashboardController);

  DashboardController.$inject = ['$scope', '$http', '$location', '$timeout',
                                'orchestraTasks'];

  function DashboardController($scope, $http, $location, $timeout,
                               orchestraTasks) {
    var vm = this;

    // Surface service to interpolator
    vm.orchestraTasks = orchestraTasks;

    vm.waiting = true;
    orchestraTasks.data.finally(function() {
      vm.waiting = false;
    });

    vm.waiting = false;

    vm.newTask = function(taskType) {
      // To allow users to read the "no tasks left" message while debouncing
      // further clicks, we leave the message up for 15 seconds before removing
      // it and re-enabling the buttons
      vm.waiting = true;
      if (!vm.noTaskTimer) {
        // Initialize task timer to dummy value to prevent subsequent API calls
        vm.noTaskTimer = 'temp';
        orchestraTasks.newTask(taskType)
          .then(function(response) {
            $location.path('task/' + data.id);
            vm.noTaskTimer = undefined;
            vm.waiting = false;
          }, function(response) {
            vm.newTaskError = true;
            // Rate limit button-clicking
            vm.noTaskTimer = $timeout(function() {
              vm.noTaskTimer = undefined;
              vm.newTaskError = false;
            }, 15000);
          });
      }
    };
  }
})();
