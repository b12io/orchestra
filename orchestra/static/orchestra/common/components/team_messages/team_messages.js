(function() {
  'use strict';

  angular
    .module('orchestra.common')
    .directive('orchestraTeamMessages', function() {
      return {
        restrict: 'E',
        controllerAs: 'vm',
        controller: function($scope, orchestraService) {
          var vm = this;
          vm.taskAssignment = $scope.taskAssignment;
        },
        templateUrl: $static('/static/orchestra/common/components/team_messages/team_messages.html')
      };
    });
})();
