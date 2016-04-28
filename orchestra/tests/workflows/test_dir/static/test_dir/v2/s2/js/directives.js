(function() {
  'use strict';

  angular.module('test_dir.v2.s2').directive(
    's2', function() {
      return {
        restrict: 'E',
        controller: 'S2Controller',
        scope: {
          taskAssignment: '=',
        },
        templateUrl: $static('/static/test_dir/v2/s2/partials/s2.html'),
      };
    });
})();
