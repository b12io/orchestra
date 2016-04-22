(function() {
  'use strict';

  angular
    .module('journalism_workflow.v1.copy_editor')
    .controller('CopyEditorController', CopyEditorController);

  CopyEditorController.$inject = ['$scope', 'orchestraService'];

  function CopyEditorController($scope, orchestraService) {
    var vm = $scope;

    // Store the article text document URL for easier summary later
    var documentCreationStep = vm.taskAssignment.prerequisites.document_creation;
    vm.taskAssignment.articleDocument = documentCreationStep.articleURL;

    // Set up the photos for captioning
    vm.taskAssignment.task.data.photos = [];
    var photoAdjustStep = vm.taskAssignment.prerequisites.photo_adjustment;
    var photos = photoAdjustStep.photos_for_caption;
    for (var i = 0; i < photos.length; i++) {
      vm.taskAssignment.task.data.photos.push({
        src: photos[i],
        caption: ''
      });
    }
  }
})();
