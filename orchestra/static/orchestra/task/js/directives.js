(function () {
  'use strict';

  angular.module('orchestra.task.directives').directive('websiteIframe', function() {
    return {
      restrict: 'E',
      controller: 'IframeController',
      scope: {
        title: '@',
        id: '@',
        description: '@',
        iframeUrl: '@',
        externalUrl: '@'
      },
      templateUrl: '/static/orchestra/task/partials/website_iframe.html',
    };
  });

  angular.module('orchestra.task.directives').directive(
    'bareIframe', function() {
      return {
	restrict: 'E',
	controller: 'IframeController',
	scope: {
	  title: '@',
          id: '@',
          description: '@',
          iframeUrl: '@',
          externalUrl: '@'
	},
	templateUrl: '/static/orchestra/task/partials/bare_iframe.html',
      };
    });

  angular
    .module('orchestra.task.directives')
    .directive('dynamicLoad', dynamicLoad);


  dynamicLoad.$inject = ['$compile'];

  function dynamicLoad($compile) {
    return {
      restrict: 'A',
      replace: true,
      link: function (scope, ele, attrs) {
        scope.$watch(attrs.dynamicLoad, function(html) {
          ele.html(html);
          $compile(ele.contents())(scope);
        });
      }
    };
  }


})();
