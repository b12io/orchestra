(function() {
  'use strict';

  angular
    .module('orchestra.project_management')
    .controller('ProjectManagementController', ProjectManagementController);

  function ProjectManagementController($route, $routeParams, $scope, projectVis, dataService) {
    var vm = this;
    $scope.activate = function() {
      if (dataService.currentProject.id) {
        $route.updateParams({projectId: dataService.currentProject.id});
      }
      projectVis.setup($scope, '.project-management .svg-wrapper', $routeParams.projectId);
    };
    $scope.activate();
  }
})();
