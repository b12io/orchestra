import template from './taskcards.html'

export default function taskcards () {
  return {
    template,
    restrict: 'A',
    scope: {
      taskcards: '='
    }
  }
}
