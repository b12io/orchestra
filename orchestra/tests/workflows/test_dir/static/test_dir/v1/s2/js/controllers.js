(function() {
  'use strict';

  angular
    .module('test_dir.v1.s2')
    .controller('S2Controller', S2Controller)

  S2Controller.$inject = ['$scope', 'orchestraService'];

  function S2Controller($scope, orchestraService) {
    var vm = $scope;
  }
})();
