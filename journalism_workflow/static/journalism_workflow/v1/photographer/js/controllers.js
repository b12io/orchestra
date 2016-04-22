(function() {
  'use strict';

  angular
    .module('journalism_workflow.v1.photographer')
    .controller('ImageUploadController', ImageUploadController)

  ImageUploadController.$inject = ['$scope', 'orchestraService'];

  function ImageUploadController($scope, orchestraService) {
    var vm = $scope;
    var editorStep = vm.taskAssignment.prerequisites.article_planning;
    vm.who = editorStep.who;
    vm.what = editorStep.what;
    vm.when = editorStep.when;
    vm.where = editorStep.where;
    vm.notes = editorStep.notes;
  }
})();
