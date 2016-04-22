(function() {
  'use strict';

  angular
    .module('orchestra.dashboard')
    .directive('taskcards', taskcards);

  function taskcards() {
    return {
      restrict: 'A',
      scope: {
        taskcards: '='
      },
      templateUrl: $static('/static/orchestra/dashboard/partials/taskcards.html')
    };
  }
})();
