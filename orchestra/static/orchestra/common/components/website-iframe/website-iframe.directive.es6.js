import template from './website-iframe.html'
import './website-iframe.scss'

export default function websiteIframe ($compile, $sce, $timeout) {
  'ngAnnotate'
  return {
    template,
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
    link: function ($scope, el, attr) {
      // The iframe is actually added only after everything is loaded.
      // This way the webpage does not stall for a couple of seconds until
      // all the iframe directives load.
      $timeout(function () {
        var iframe = document.createElement('iframe')
        var iframeAttrs = {
          'name': '{{title}}',
          'class': 'website-iframe',
          'id': 'iframe-' + $scope.id,
          'frameBorder': 0,
          'height': $scope.height || '400px'
        }
        for (var attr in iframeAttrs) {
          iframe.setAttribute(attr, iframeAttrs[attr])
        }

        var iframeWrapper = document.getElementById('iframe-wrapper-' + $scope.id).parentElement
        iframeWrapper.style.height = $scope.height || '400px'

        var parent = document.getElementById('iframe-wrapper-' + $scope.id)
        parent.appendChild(iframe)
        $scope.iframe = iframe

        // The iframe directive runs before the iframeUrl is $applied (in cases
        // where it is dynamically populated by a service, e.g. googleUtils),
        // so we watch for its update.
        $scope.$watch('iframeUrl', function (newVal, oldVal) {
          $scope.trustedIframeUrl = $sce.trustAsResourceUrl($scope.iframeUrl)
          $scope.iframe.setAttribute('ng-src', '{{trustedIframeUrl}}')
          $compile($scope.iframe)($scope)
        }, true)
      })
    }
  }
}
