(function() {
  // 'use strict';

  angular.module('orchestra.timecard')
    .controller('TimecardController', function($routeParams, $scope, timecardService) {
      // var vm = this;
      vm = this;
      vm.taskId = $routeParams.taskId;

      vm.timecardService = timecardService;

      vm.prettyDate = function(dateString) {
        // TODO(jrbotros): fix groupby with custom comparator
        return moment(dateString).format('MMMM D');
      };
    });
})();
