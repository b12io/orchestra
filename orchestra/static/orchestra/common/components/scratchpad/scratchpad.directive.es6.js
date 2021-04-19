import template from './scratchpad.html'

export default function orchestraScratchpad () {
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
