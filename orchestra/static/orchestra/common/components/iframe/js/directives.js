(function () {
  'use strict';

  angular
    .module('orchestra.common')
    .directive('websiteIframe', ['$compile', '$sce', '$timeout', websiteIframe]);

  function websiteIframe($compile, $sce, $timeout) {
    return {
      restrict: 'E',
      scope: {
        'title': '@',
        'id': '@',
        'description': '@',
        'iframeUrl': '@',
        'externalUrl': '@',
        'height': '@?',
        'bare': '@?'
      },
      link: function($scope, el, attr) {
        // The iframe is actually added only after everything is loaded.
        // This way the webpage does not stall for a couple of seconds until
        // all the iframe directives load.
        $timeout(function(){
          var iframe = document.createElement('iframe');
          var iframeAttrs = {
            'name': '{{title}}',
            'class': 'website-iframe',
            'id': 'iframe-' + $scope.id,
            'frameBorder': 0,
            'height': $scope.height || 400,
          };
          for (var attr in iframeAttrs) {
            iframe.setAttribute(attr, iframeAttrs[attr]);
          }

          var parent = document.getElementById('iframe-wrapper-' + $scope.id);
          parent.appendChild(iframe);
          $scope.iframe = iframe;

          // The iframe directive runs before the iframeUrl is $applied (in cases
          // where it is dynamically populated by a service, e.g. googleUtils),
          // so we watch for its update.
          $scope.$watch('iframeUrl', function(newVal, oldVal) {
            $scope.trustedIframeUrl = $sce.trustAsResourceUrl($scope.iframeUrl);
            $scope.iframe.setAttribute('ng-src','{{trustedIframeUrl}}');
            $compile($scope.iframe)($scope);
          }, true);
        });
      },
      templateUrl: $static('/static/orchestra/common/components/iframe/partials/website_iframe.html')
    };
  }
})();
