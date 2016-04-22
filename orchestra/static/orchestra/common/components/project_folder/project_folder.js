(function() {
  'use strict';

  angular
    .module('orchestra.common')
    .directive('orchestraProjectFolder', function() {
      return {
        restrict: 'E',
        controllerAs: 'vm',
        controller: function($scope, orchestraService) {
          var vm = this;

          vm.taskAssignment = $scope.taskAssignment;
          vm.projectFolderId = vm.taskAssignment.project.project_data.project_folder_id;
          vm.projectFolderEmbedUrl = orchestraService.googleUtils.folders.embedListUrl(vm.projectFolderId);
          vm.projectFolderExternalUrl = orchestraService.googleUtils.folders.externalUrl(vm.projectFolderId);
        },
        templateUrl: $static('/static/orchestra/common/components/project_folder/project_folder.html')
      };
    });
})();
