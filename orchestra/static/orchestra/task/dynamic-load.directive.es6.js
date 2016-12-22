export default function dynamicLoad ($compile) {
  'ngAnnotate'
  return {
    restrict: 'A',
    replace: true,
    link: function (scope, ele, attrs) {
      scope.$watch(attrs.dynamicLoad, function (html) {
        ele.html(html)
        $compile(ele.contents())(scope)
      })
    }
  }
}
