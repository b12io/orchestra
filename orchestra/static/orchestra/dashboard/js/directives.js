(function() {
  'use strict';

  angular
    .module('orchestra.dashboard.directives')
    .directive('taskcards', taskcards);

  function taskcards() {
    return {
      restrict: 'A',
      scope: {
        taskcards: '='
      },
      templateUrl: '/static/orchestra/dashboard/partials/taskcards.html'
    };
  }
})();
