(function () {
  'use strict';

  angular
    .module('journalism_workflow.v1.copy_editor.controllers')
    .controller('CopyEditorController', CopyEditorController)

  CopyEditorController.$inject = ['$scope', 'orchestraService'];

  function CopyEditorController($scope, orchestraService) {
    var vm = $scope;

    // Store the article text document URL for easier summary later
    var documentCreationStep = orchestraService.taskUtils.findPrerequisite(
      vm.taskAssignment, 'document_creation')
    vm.taskAssignment.task.data.articleDocument = documentCreationStep.task.data.articleURL;

    // Set up the photos for captioning
    vm.taskAssignment.task.data.photos = [];
    var photoAdjustStep = orchestraService.taskUtils.findPrerequisite(
      vm.taskAssignment, 'photo_adjustment');
    var photos = photoAdjustStep.task.data.photos_for_caption;
    for (var i = 0; i < photos.length; i++) {
      vm.taskAssignment.task.data.photos.push({
	src: photos[i],
	caption: ''
      });
    }
  }
})();
