(function() {
  'use strict';

  angular
    .module('simple_workflow.v1.rate')
    .controller('ImageRatingController', ImageRatingController);

  ImageRatingController.$inject = ['$scope', 'orchestraService'];

  function ImageRatingController($scope, orchestraService) {
    var vm = $scope;
    var crawlStep = vm.taskAssignment.prerequisites.crawl;
    if (crawlStep.status !== 'success') {
      vm.imageURL = "http://media.giphy.com/media/2vA33ikUb0Qz6/giphy.gif";
      vm.success = false;
    } else {
      vm.imageURL = crawlStep.image;
      vm.success = true;
    }
  }
})();
