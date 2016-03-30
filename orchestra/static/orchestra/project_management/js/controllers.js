(function() {
  'use strict';

  angular
    .module('orchestra.project_management.controllers')
    .controller('ProjectManagementController', ProjectManagementController);

  function ProjectManagementController($location, $scope, $routeParams, $http, $sce,
    $compile, $modal, $timeout, projectVis) {
    var vm = this;
    $scope.activate = function() {
      projectVis.setup($scope, $routeParams.projectId, '.project-management .svg-wrapper');
    };
    $scope.activate();
  }
})();
