import template from './time-input.html'
import './time-input.scss'

export default function timeInput () {
  return {
    template,
    scope: {
      datetime: '='
    },
    link: (scope, elem, attrs) => {
      scope.onChange = () => {
        scope.datetime.hours(scope.timeDisplay.getHours())
        scope.datetime.minutes(scope.timeDisplay.getMinutes())
      }

      scope.$watch(() => {
        return scope.datetime
      }, () => {
        if (scope.datetime) {
          scope.datetime.seconds(0)
          scope.datetime.milliseconds(0)
          scope.timeDisplay = scope.datetime.toDate()
        } else {
          scope.timeDisplay = null
        }
      })
    }
  }
}
