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
    $scope.projectDescription = function(project) {
      // Protect against placeholder text that has no datetime
      if (angular.isUndefined(project.start_datetime)) {
        return project.short_description;
      }
      return project.short_description + ' (' + moment(project.start_datetime).format('YYYY-MM-DD HH:mm') + ')';
    };
    $scope.activate();
  }
})();
