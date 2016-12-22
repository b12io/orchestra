import template from './team-messages.html'

export default function orchestraTeamMessages () {
  return {
    template,
    restrict: 'E',
    controllerAs: 'vm',
    controller: function ($scope, orchestraService) {
      var vm = this
      vm.taskAssignment = $scope.taskAssignment
    }
  }
}
