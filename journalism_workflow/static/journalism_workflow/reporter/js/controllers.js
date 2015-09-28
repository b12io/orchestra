(function () {
  'use strict';

  angular
    .module('journalism_workflow.reporter.controllers')
    .controller('ArticleWritingController', ArticleWritingController)

  ArticleWritingController.$inject = ['$scope', 'orchestraService'];

  function ArticleWritingController($scope, orchestraService) {
    var vm = $scope;
    var editorStep = orchestraService.taskUtils.findPrerequisite(
      vm.taskAssignment, 'article_planning');
    vm.who = editorStep.task.data.who;
    vm.what = editorStep.task.data.what;
    vm.when = editorStep.task.data.when;
    vm.where = editorStep.task.data.where;
    vm.notes = editorStep.task.data.notes;

    var documentCreationStep = orchestraService.taskUtils.findPrerequisite(
      vm.taskAssignment, 'document_creation');
    vm.articleURL = documentCreationStep.task.data.articleURL;
  }
})();
