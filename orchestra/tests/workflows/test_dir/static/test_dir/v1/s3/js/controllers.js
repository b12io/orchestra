(function() {
  'use strict';

  angular
    .module('test_dir.v1.s3')
    .controller('S3Controller', S3Controller)

  S3Controller.$inject = ['$scope', 'orchestraService'];

  function S3Controller($scope, orchestraService) {
    var vm = $scope;
  }
})();
