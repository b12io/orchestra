(function () {
  'use strict';

  angular
    .module('journalism_workflow.v1.photographer.controllers')
    .controller('ImageUploadController', ImageUploadController)

  ImageUploadController.$inject = ['$scope', 'orchestraService'];

  function ImageUploadController($scope, orchestraService) {
    var vm = $scope;
    var editorStep = orchestraService.taskUtils.findPrerequisite(
      vm.taskAssignment, 'article_planning');
    vm.who = editorStep.task.data.who;
    vm.what = editorStep.task.data.what;
    vm.when = editorStep.task.data.when;
    vm.where = editorStep.task.data.where;
    vm.notes = editorStep.task.data.notes;
  }
})();
