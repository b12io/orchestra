(function() {
  'use strict';

  angular
    .module('journalism_workflow.v1.reporter')
    .controller('ArticleWritingController', ArticleWritingController);

  ArticleWritingController.$inject = ['$scope', 'orchestraService'];

  function ArticleWritingController($scope, orchestraService) {
    var vm = $scope;
    var editorStep = vm.taskAssignment.prerequisites.article_planning;
    vm.who = editorStep.who;
    vm.what = editorStep.what;
    vm.when = editorStep.when;
    vm.where = editorStep.where;
    vm.notes = editorStep.notes;

    var documentCreationStep = vm.taskAssignment.prerequisites.document_creation;
    vm.articleURL = documentCreationStep.articleURL;
  }
})();
