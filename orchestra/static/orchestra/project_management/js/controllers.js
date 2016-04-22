(function() {
  'use strict';

  angular
    .module('orchestra.project_management')
    .controller('ProjectManagementController', ProjectManagementController);

  function ProjectManagementController($location, $scope, $routeParams, $http, $sce,
    $compile, $uibModal, $timeout, projectVis) {
    var vm = this;
    $scope.activate = function() {
      projectVis.setup($scope, $routeParams.projectId, '.project-management .svg-wrapper');
    };
    $scope.activate();
  }
})();
