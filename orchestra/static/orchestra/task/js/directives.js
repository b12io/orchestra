(function() {
  'use strict';

  angular
    .module('orchestra.task')
    .directive('dynamicLoad', dynamicLoad);


  dynamicLoad.$inject = ['$compile'];

  function dynamicLoad($compile) {
    return {
      restrict: 'A',
      replace: true,
      link: function(scope, ele, attrs) {
        scope.$watch(attrs.dynamicLoad, function(html) {
          ele.html(html);
          $compile(ele.contents())(scope);
        });
      }
    };
  }

})();
