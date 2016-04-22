(function() {
  'use strict';

  angular.module('test_dir.v1.s3').directive(
    's3', function() {
      return {
        restrict: 'E',
        controller: 'S3Controller',
        scope: {
          taskAssignment: '=',
        },
        templateUrl: $static('/static/test_dir/v1/s3/partials/s3.html'),
      };
    });
})();
